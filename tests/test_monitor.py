"""Tests for the monitor module."""

import time
from collections import deque
from unittest.mock import MagicMock, patch

import pytest
from rich.layout import Layout
from rich.panel import Panel

from es_translator.monitor import MonitorStats, TranslationMonitor


class TestMonitorStats:
    """Tests for MonitorStats dataclass."""

    def test_default_values(self):
        """Test that MonitorStats initializes with correct defaults."""
        stats = MonitorStats()

        assert stats.total_tasks == 0
        assert stats.completed_tasks == 0
        assert stats.pending_tasks == 0
        assert stats.active_tasks == 0
        assert stats.failed_tasks == 0
        assert stats.workers == {}
        assert isinstance(stats.throughput_history, deque)
        assert len(stats.throughput_history) == 0
        assert stats.peak_throughput == 0.0
        assert stats.last_completed_count == 0
        assert stats.initial_pending is None

    def test_throughput_history_maxlen(self):
        """Test that throughput_history has maxlen of 60."""
        stats = MonitorStats()

        # Add more than 60 items
        for i in range(100):
            stats.throughput_history.append(i)

        assert len(stats.throughput_history) == 60
        # Should keep the last 60 items
        assert stats.throughput_history[0] == 40
        assert stats.throughput_history[-1] == 99


class TestTranslationMonitor:
    """Tests for TranslationMonitor class."""

    @pytest.fixture
    def monitor(self):
        """Create a TranslationMonitor instance for testing."""
        with patch('es_translator.monitor.Celery'):
            return TranslationMonitor(
                broker_url='redis://localhost:6379/0',
                refresh_interval=5.0,
            )

    def test_init(self, monitor):
        """Test TranslationMonitor initialization."""
        assert monitor.broker_url == 'redis://localhost:6379/0'
        assert monitor.refresh_interval == 5.0
        assert isinstance(monitor.stats, MonitorStats)

    def test_init_defaults(self):
        """Test TranslationMonitor initialization with defaults."""
        with patch('es_translator.monitor.Celery'):
            monitor = TranslationMonitor(
                broker_url='redis://localhost:6379/0',
            )

        assert monitor.refresh_interval == 2.0

    def test_get_celery_stats(self, monitor):
        """Test fetching Celery stats."""
        mock_inspect = MagicMock()
        mock_inspect.active.return_value = {
            'worker1@host': [{'id': 'task1'}, {'id': 'task2'}],
            'worker2@host': [{'id': 'task3'}],
        }
        mock_inspect.reserved.return_value = {
            'worker1@host': [{'id': 'task4'}],
            'worker2@host': [],
        }
        mock_inspect.stats.return_value = {
            'worker1@host': {
                'prefetch_count': 4,
                'total': {'es_translator.tasks.translate_document_task': 100},
            },
            'worker2@host': {
                'prefetch_count': 4,
                'total': {'es_translator.tasks.translate_document_task': 50},
            },
        }

        monitor.celery_app.control.inspect.return_value = mock_inspect

        # Mock Redis to avoid actual connection (imported inside function)
        with patch.dict('sys.modules', {'redis': MagicMock()}):
            import sys

            mock_redis = MagicMock()
            mock_redis.llen.return_value = 10
            sys.modules['redis'].Redis.from_url.return_value = mock_redis

            monitor.get_celery_stats()

        assert monitor.stats.active_tasks == 3
        assert monitor.stats.pending_tasks == 11  # 10 from queue + 1 reserved
        assert monitor.stats.completed_tasks == 150  # 100 + 50 from workers
        assert len(monitor.stats.workers) == 2
        assert monitor.stats.workers['worker1@host']['active'] == 2
        assert monitor.stats.workers['worker1@host']['processed'] == 100
        # Total tasks should be calculated
        assert monitor.stats.total_tasks == 164  # 11 pending + 3 active + 150 completed

    def test_get_celery_stats_no_workers(self, monitor):
        """Test Celery stats when no workers are connected."""
        mock_inspect = MagicMock()
        mock_inspect.active.return_value = None
        mock_inspect.reserved.return_value = None
        mock_inspect.stats.return_value = None

        monitor.celery_app.control.inspect.return_value = mock_inspect

        monitor.get_celery_stats()

        assert monitor.stats.active_tasks == 0
        assert monitor.stats.pending_tasks == 0
        assert monitor.stats.completed_tasks == 0
        assert monitor.stats.workers == {}

    def test_get_celery_stats_tracks_initial_total(self, monitor):
        """Test that initial total is captured and used for progress."""
        mock_inspect = MagicMock()
        mock_inspect.active.return_value = {'worker1@host': [{'id': 'task1'}]}
        mock_inspect.reserved.return_value = {'worker1@host': []}
        mock_inspect.stats.return_value = {
            'worker1@host': {
                'prefetch_count': 4,
                'total': {'es_translator.tasks.translate_document_task': 10},
            },
        }

        monitor.celery_app.control.inspect.return_value = mock_inspect

        # First call - captures initial pending
        monitor.get_celery_stats()
        initial_total = monitor.stats.total_tasks
        assert monitor.stats.initial_pending == initial_total

        # Simulate progress - more tasks completed
        mock_inspect.stats.return_value = {
            'worker1@host': {
                'prefetch_count': 4,
                'total': {'es_translator.tasks.translate_document_task': 20},
            },
        }

        monitor.get_celery_stats()
        # Total should still be based on initial or current max
        assert monitor.stats.total_tasks >= initial_total

    def test_get_celery_stats_initializes_throughput_baseline(self, monitor):
        """Test that first stats fetch initializes last_completed_count to avoid spike."""
        mock_inspect = MagicMock()
        mock_inspect.active.return_value = {'worker1@host': []}
        mock_inspect.reserved.return_value = {'worker1@host': []}
        mock_inspect.stats.return_value = {
            'worker1@host': {
                'prefetch_count': 4,
                'total': {'es_translator.tasks.translate_document_task': 500},
            },
        }

        monitor.celery_app.control.inspect.return_value = mock_inspect

        # First call should initialize last_completed_count to current completed
        monitor.get_celery_stats()
        assert monitor.stats.completed_tasks == 500
        assert monitor.stats.last_completed_count == 500

        # Now if we calculate throughput, delta should be 0 (not 500)
        monitor.stats.last_check_time = time.time() - 10  # 10 seconds ago
        monitor.update_throughput()

        assert len(monitor.stats.throughput_history) == 1
        assert monitor.stats.throughput_history[0] == 0.0

    def test_update_throughput(self, monitor):
        """Test throughput calculation based on completed tasks."""
        # Set initial state
        monitor.stats.last_check_time = time.time() - 10  # 10 seconds ago
        monitor.stats.last_completed_count = 100
        monitor.stats.completed_tasks = 150

        monitor.update_throughput()

        assert len(monitor.stats.throughput_history) == 1
        # 50 tasks in ~10 seconds = ~5 tasks/sec
        assert 4.0 <= monitor.stats.throughput_history[0] <= 6.0
        assert monitor.stats.last_completed_count == 150

    def test_update_throughput_tracks_session_peak(self, monitor):
        """Test that peak throughput tracks session maximum."""
        assert monitor.stats.peak_throughput == 0.0

        # First update: 10 tasks/sec
        monitor.stats.last_check_time = time.time() - 10
        monitor.stats.last_completed_count = 0
        monitor.stats.completed_tasks = 100
        monitor.update_throughput()
        assert monitor.stats.peak_throughput == pytest.approx(10.0, rel=0.01)

        # Second update: 5 tasks/sec (lower, peak should stay at 10)
        monitor.stats.last_check_time = time.time() - 10
        monitor.stats.completed_tasks = 150
        monitor.update_throughput()
        assert monitor.stats.peak_throughput == pytest.approx(10.0, rel=0.01)

        # Third update: 20 tasks/sec (higher, peak should update)
        monitor.stats.last_check_time = time.time() - 10
        monitor.stats.completed_tasks = 350
        monitor.update_throughput()
        assert monitor.stats.peak_throughput == pytest.approx(20.0, rel=0.01)

    def test_update_throughput_skips_if_too_soon(self, monitor):
        """Test that throughput is not updated if refresh interval hasn't passed."""
        monitor.stats.last_check_time = time.time()  # Just now

        monitor.update_throughput()

        assert len(monitor.stats.throughput_history) == 0

    def test_create_header(self, monitor):
        """Test header panel creation."""
        panel = monitor.create_header()

        assert isinstance(panel, Panel)

    def test_create_progress_panel(self, monitor):
        """Test progress panel creation."""
        monitor.stats.total_tasks = 1000
        monitor.stats.completed_tasks = 500
        monitor.stats.pending_tasks = 400
        monitor.stats.active_tasks = 100

        panel = monitor.create_progress_panel()

        assert isinstance(panel, Panel)
        assert panel.title == 'Progress'

    def test_create_progress_panel_with_eta(self, monitor):
        """Test progress panel with ETA calculation."""
        monitor.stats.total_tasks = 1000
        monitor.stats.completed_tasks = 500
        monitor.stats.pending_tasks = 400
        monitor.stats.active_tasks = 100
        monitor.stats.throughput_history = deque([2.0, 2.5, 2.0])  # ~2 tasks/sec avg

        panel = monitor.create_progress_panel()

        assert isinstance(panel, Panel)

    def test_create_progress_panel_zero_total(self, monitor):
        """Test progress panel handles zero total gracefully."""
        monitor.stats.total_tasks = 0
        monitor.stats.completed_tasks = 0

        panel = monitor.create_progress_panel()

        assert isinstance(panel, Panel)

    def test_create_queue_panel(self, monitor):
        """Test queue panel creation."""
        monitor.stats.pending_tasks = 100
        monitor.stats.active_tasks = 4
        monitor.stats.completed_tasks = 50
        monitor.stats.workers = {'worker1': {}, 'worker2': {}}

        panel = monitor.create_queue_panel()

        assert isinstance(panel, Panel)
        assert panel.title == 'Queue Status'

    def test_create_throughput_panel_no_data(self, monitor):
        """Test throughput panel when no data is available."""
        panel = monitor.create_throughput_panel()

        assert isinstance(panel, Panel)
        assert panel.title == 'Throughput'

    def test_create_throughput_panel_with_data(self, monitor):
        """Test throughput panel with historical data."""
        monitor.stats.throughput_history = deque([1.0, 2.0, 3.0, 2.5, 1.5])

        panel = monitor.create_throughput_panel()

        assert isinstance(panel, Panel)

    def test_create_workers_panel_no_workers(self, monitor):
        """Test workers panel when no workers are connected."""
        panel = monitor.create_workers_panel()

        assert isinstance(panel, Panel)
        assert panel.title == 'Workers'

    def test_create_workers_panel_with_workers(self, monitor):
        """Test workers panel with connected workers."""
        monitor.stats.workers = {
            'celery@worker1': {'active': 2, 'reserved': 1, 'processed': 100, 'throughput': 5.0},
            'celery@worker2': {'active': 1, 'reserved': 0, 'processed': 50, 'throughput': 2.5},
        }

        panel = monitor.create_workers_panel()

        assert isinstance(panel, Panel)

    def test_create_workers_panel_truncates_long_names(self, monitor):
        """Test that long worker names are truncated."""
        monitor.stats.workers = {
            'celery@very-long-worker-hostname-that-exceeds-limit': {
                'active': 1,
                'reserved': 0,
                'processed': 10,
                'throughput': 1.0,
            },
        }

        panel = monitor.create_workers_panel()

        assert isinstance(panel, Panel)

    def test_init_layout(self, monitor):
        """Test layout creation."""
        monitor._init_layout()

        assert isinstance(monitor.layout, Layout)

    def test_refresh_stats(self, monitor):
        """Test that refresh_stats calls all stat methods."""
        monitor.get_celery_stats = MagicMock()
        monitor.update_throughput = MagicMock()

        monitor.refresh_stats()

        monitor.get_celery_stats.assert_called_once()
        monitor.update_throughput.assert_called_once()

    def test_update_panels(self, monitor):
        """Test panels update."""
        monitor._init_layout()
        # Should not raise
        monitor._update_panels()

        assert isinstance(monitor.layout, Layout)

    def test_run_keyboard_interrupt(self, monitor):
        """Test that run handles KeyboardInterrupt gracefully."""
        monitor.refresh_stats = MagicMock()

        with patch('es_translator.monitor.Live') as mock_live:
            # Make Live raise KeyboardInterrupt when entering context
            mock_live.return_value.__enter__ = MagicMock(side_effect=KeyboardInterrupt)
            mock_live.return_value.__exit__ = MagicMock(return_value=False)

            # Should not raise
            monitor.run()


class TestMonitorCLI:
    """Tests for the monitor CLI command."""

    def test_monitor_command_exists(self):
        """Test that the monitor command is registered."""
        from es_translator.cli import monitor

        assert monitor is not None
        assert hasattr(monitor, 'callback')

    def test_monitor_command_options(self):
        """Test that monitor command has expected options."""
        from es_translator.cli import monitor

        option_names = [param.name for param in monitor.params]

        assert 'broker_url' in option_names
        assert 'refresh' in option_names
