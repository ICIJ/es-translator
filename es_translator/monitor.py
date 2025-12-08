"""Live monitoring for es-translator workers.

This module provides an htop/nvtop-like live monitoring interface for
es-translator Celery workers, showing queue status, translation progress,
and throughput metrics.
"""

import re
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import plotext as plt
from celery import Celery
from rich.console import Console, ConsoleOptions, RenderResult
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class ThroughputChart:
    """A Rich renderable that creates a plotext chart sized to fit the available space."""

    def __init__(self, history: list, current: float, avg: float, peak: float):
        self.history = history
        self.current = current
        self.avg = avg
        self.peak = peak

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """Render the chart to fit available space."""
        width = options.max_width - 8  # Account for panel borders and right axis
        height = options.height or 10
        height = max(height - 3, 4)  # Account for header line and padding, minimum 4

        # Calculate chart data points and position data on the right
        chart_data_points = width * 2  # Approximate data points that fit in width
        data_len = len(self.history)

        # Use x coordinates to position data on the right side of the chart
        x_start = max(0, chart_data_points - data_len)
        x_coords = list(range(x_start, x_start + data_len))

        # Create minimalist plotext chart
        plt.clear_figure()
        plt.theme('clear')
        plt.plot(x_coords, self.history, marker='braille')
        plt.plotsize(width, height)
        plt.frame(False)
        plt.xticks([])
        plt.yticks([])
        plt.xlim(0, chart_data_points)
        plt.ylim(0, None)  # Force 0-based Y axis

        # Get the plot as string and strip ANSI codes
        chart_str = plt.build()
        chart_str = re.sub(r'\x1b\[[0-9;]*m', '', chart_str)

        # Build content with stats header
        header = Text()
        header.append(f'{self.current:.2f}', style='bold green')
        header.append(' current  ', style='dim')
        header.append(f'{self.avg:.2f}', style='bold cyan')
        header.append(' avg  ', style='dim')
        header.append(f'{self.peak:.2f}', style='bold yellow')
        header.append(' peak tasks/sec', style='dim')

        yield header

        # Add right axis with scale
        chart_lines = chart_str.rstrip('\n').split('\n')
        max_val = self.peak if self.peak > 0 else 1

        for i, line in enumerate(chart_lines):
            row = Text(line)
            # Add axis labels: top, middle, bottom
            if i == 0:
                row.append(f'│{max_val:>5.1f}', style='dim')
            elif i == len(chart_lines) // 2:
                row.append(f'│{max_val / 2:>5.1f}', style='dim')
            elif i == len(chart_lines) - 1:
                row.append('│  0.0', style='dim')
            else:
                row.append('│', style='dim')
            yield row


@dataclass
class MonitorStats:
    """Container for monitoring statistics."""

    # Task-based progress stats
    total_tasks: int = 0
    completed_tasks: int = 0
    pending_tasks: int = 0
    active_tasks: int = 0
    failed_tasks: int = 0

    # Worker stats
    workers: dict = field(default_factory=dict)
    worker_last_processed: dict = field(default_factory=dict)  # For per-worker throughput

    # Throughput tracking (tasks per interval)
    throughput_history: deque = field(default_factory=lambda: deque(maxlen=60))
    peak_throughput: float = 0.0  # Session peak (not just history window)
    last_completed_count: int = 0
    last_check_time: float = field(default_factory=time.time)

    # Timing
    start_time: float = field(default_factory=time.time)

    # Initial task count (captured at start to calculate total)
    initial_pending: Optional[int] = None


class TranslationMonitor:
    """Live monitoring interface for es-translator workers."""

    def __init__(
        self,
        broker_url: str,
        refresh_interval: float = 2.0,
    ):
        """Initialize the monitor.

        Args:
            broker_url: Celery broker URL (Redis).
            refresh_interval: How often to refresh stats (seconds).
        """
        self.broker_url = broker_url
        self.refresh_interval = refresh_interval

        self.celery_app = Celery('EsTranslator', broker=broker_url)
        self.celery_app.conf.task_default_queue = 'es_translator:default'
        self.console = Console()
        self.stats = MonitorStats()

    def get_celery_stats(self) -> None:
        """Fetch queue and worker stats from Celery/Redis."""
        try:
            inspect = self.celery_app.control.inspect()

            # Get active tasks per worker
            active = inspect.active() or {}
            self.stats.active_tasks = sum(len(tasks) for tasks in active.values())

            # Get reserved (pending) tasks per worker
            reserved = inspect.reserved() or {}
            reserved_count = sum(len(tasks) for tasks in reserved.values())

            # Get queue length from Redis directly for more accurate pending count
            queue_length = 0
            try:
                from redis import Redis

                redis_client = Redis.from_url(self.broker_url)
                queue_length = redis_client.llen('es_translator:default')
            except Exception:
                pass

            self.stats.pending_tasks = queue_length + reserved_count

            # Get worker info and calculate completed tasks
            stats = inspect.stats() or {}
            self.stats.workers = {}
            total_processed = 0

            current_time = time.time()
            elapsed = current_time - self.stats.last_check_time

            for worker_name, worker_stats in stats.items():
                worker_active = len(active.get(worker_name, []))
                worker_reserved = len(reserved.get(worker_name, []))
                processed = worker_stats.get('total', {}).get('es_translator.tasks.translate_document_task', 0)
                total_processed += processed

                # Calculate per-worker throughput
                last_processed = self.stats.worker_last_processed.get(worker_name, processed)
                if elapsed > 0 and self.stats.initial_pending is not None:
                    worker_throughput = (processed - last_processed) / elapsed
                else:
                    worker_throughput = 0.0
                self.stats.worker_last_processed[worker_name] = processed

                self.stats.workers[worker_name] = {
                    'active': worker_active,
                    'reserved': worker_reserved,
                    'prefetch_count': worker_stats.get('prefetch_count', 0),
                    'processed': processed,
                    'throughput': worker_throughput,
                }

            self.stats.completed_tasks = total_processed

            # Capture initial state on first run
            current_total = self.stats.pending_tasks + self.stats.active_tasks + self.stats.completed_tasks
            if self.stats.initial_pending is None:
                self.stats.initial_pending = current_total
                self.stats.total_tasks = current_total
                # Initialize throughput baseline so first calculation doesn't include
                # all historical completed tasks from before monitoring started
                self.stats.last_completed_count = self.stats.completed_tasks
            else:
                # Total tasks = max of initial or current (in case more tasks are added)
                self.stats.total_tasks = max(self.stats.initial_pending, current_total)

        except Exception as e:
            self.console.print(f'[red]Celery error: {e}[/red]')

    def update_throughput(self) -> None:
        """Calculate and record throughput based on completed tasks."""
        current_time = time.time()
        elapsed = current_time - self.stats.last_check_time

        if elapsed >= self.refresh_interval:
            tasks_completed = self.stats.completed_tasks - self.stats.last_completed_count
            throughput = tasks_completed / elapsed if elapsed > 0 else 0
            self.stats.throughput_history.append(throughput)
            self.stats.peak_throughput = max(self.stats.peak_throughput, throughput)
            self.stats.last_completed_count = self.stats.completed_tasks
            self.stats.last_check_time = current_time

    def create_header(self) -> Panel:
        """Create the header panel."""
        elapsed = time.time() - self.stats.start_time
        hours, remainder = divmod(int(elapsed), 3600)
        minutes, seconds = divmod(remainder, 60)

        title = Text()
        title.append('ES-TRANSLATOR MONITOR', style='bold cyan')
        title.append(f'  |  Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}', style='dim')
        title.append(f'  |  {datetime.now().strftime("%H:%M:%S")}', style='dim')

        return Panel(title, style='cyan')

    def create_progress_panel(self) -> Panel:
        """Create the translation progress panel based on tasks."""
        total = self.stats.total_tasks if self.stats.total_tasks > 0 else 1
        completed = self.stats.completed_tasks
        remaining = self.stats.pending_tasks + self.stats.active_tasks
        pct = (completed / total) * 100 if total > 0 else 0

        # Calculate ETA
        if self.stats.throughput_history:
            avg_throughput = sum(self.stats.throughput_history) / len(self.stats.throughput_history)
            if avg_throughput > 0:
                eta_seconds = remaining / avg_throughput
                eta_hours, eta_remainder = divmod(int(eta_seconds), 3600)
                eta_minutes, eta_secs = divmod(eta_remainder, 60)
                eta_str = f'{eta_hours:02d}:{eta_minutes:02d}:{eta_secs:02d}'
            else:
                eta_str = '--:--:--'
        else:
            eta_str = 'calculating'

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column('Metric', style='bold')
        table.add_column('Value', justify='right')

        table.add_row('Progress', f'[green]{pct:.1f}%[/green]')
        table.add_row('Completed', f'[cyan]{completed:,}[/cyan] / {total:,}')
        table.add_row('Remaining', f'[yellow]{remaining:,}[/yellow]')
        table.add_row('ETA', f'[dim]{eta_str}[/dim]')

        return Panel(table, title='Progress', border_style='green')

    def create_queue_panel(self) -> Panel:
        """Create the Celery queue status panel."""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column('Metric', style='bold')
        table.add_column('Value', justify='right')

        table.add_row('Pending', f'[yellow]{self.stats.pending_tasks:,}[/yellow]')
        table.add_row('Active', f'[green]{self.stats.active_tasks:,}[/green]')
        table.add_row('Completed', f'[cyan]{self.stats.completed_tasks:,}[/cyan]')
        table.add_row('Workers', f'[magenta]{len(self.stats.workers):,}[/magenta]')

        return Panel(table, title='Queue Status', border_style='yellow')

    def create_throughput_panel(self) -> Panel:
        """Create the throughput graph panel using plotext."""
        history = list(self.stats.throughput_history)

        if not history:
            return Panel(Text('Collecting data...', style='dim'), title='Throughput', border_style='blue')

        current = history[-1] if history else 0
        avg = sum(history) / len(history) if history else 0

        chart = ThroughputChart(history, current, avg, self.stats.peak_throughput)
        return Panel(chart, title='Throughput', border_style='blue')

    def create_workers_panel(self) -> Panel:
        """Create the workers status panel."""
        if not self.stats.workers:
            return Panel(Text('No workers connected', style='yellow'), title='Workers', border_style='magenta')

        table = Table(show_header=True, header_style='bold')
        table.add_column('Worker', style='cyan')
        table.add_column('Active', justify='center')
        table.add_column('Reserved', justify='center')
        table.add_column('Processed', justify='right')
        table.add_column('Tasks/s', justify='right')

        for worker_name, info in self.stats.workers.items():
            # Shorten worker name for display
            short_name = worker_name.split('@')[-1] if '@' in worker_name else worker_name
            if len(short_name) > 20:
                short_name = short_name[:17] + '...'

            table.add_row(
                short_name,
                f'[green]{info["active"]}[/green]',
                f'[yellow]{info["reserved"]}[/yellow]',
                f'{info["processed"]:,}',
                f'{info.get("throughput", 0):.1f}',
            )

        return Panel(table, title='Workers', border_style='magenta')

    def _init_layout(self) -> None:
        """Create and cache the main layout structure."""
        self.layout = Layout()

        self.layout.split(
            Layout(name='header', size=3),
            Layout(name='main'),
            Layout(name='footer', size=3),
        )

        self.layout['main'].split_row(
            Layout(name='left'),
            Layout(name='right', ratio=2),
        )

        self.layout['left'].split(
            Layout(name='queue'),
            Layout(name='progress'),
        )

        self.layout['right'].split(
            Layout(name='workers'),
            Layout(name='throughput'),
        )

        # Footer is static, set it once
        footer = Text()
        footer.append('Press ', style='dim')
        footer.append('Ctrl+C', style='bold')
        footer.append(' to exit  |  ', style='dim')
        footer.append(f'Refresh: {self.refresh_interval}s', style='dim')
        self.layout['footer'].update(Panel(footer, style='dim'))

        # Initialize panels with content to avoid "Layout(name=XXX)" flash
        self._update_panels()

    def refresh_stats(self) -> None:
        """Refresh all statistics."""
        self.get_celery_stats()
        self.update_throughput()

    def _update_panels(self) -> None:
        """Update all dynamic panels with current data."""
        self.layout['header'].update(self.create_header())
        self.layout['queue'].update(self.create_queue_panel())
        self.layout['workers'].update(self.create_workers_panel())
        self.layout['progress'].update(self.create_progress_panel())
        self.layout['throughput'].update(self.create_throughput_panel())

    def run(self) -> None:
        """Run the live monitoring interface."""
        self.console.print('[cyan]Starting es-translator monitor...[/cyan]')
        self.console.print(f'[dim]Broker: {self.broker_url}[/dim]')
        self.console.print()

        self._init_layout()

        try:
            with Live(
                self.layout,
                console=self.console,
                refresh_per_second=4,
                screen=True,
            ) as live:
                while True:
                    self.refresh_stats()
                    self._update_panels()
                    live.refresh()
                    time.sleep(self.refresh_interval)
        except KeyboardInterrupt:
            pass  # Exit cleanly without message (screen mode clears it anyway)
