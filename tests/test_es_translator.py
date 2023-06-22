import unittest
from tempfile import mkdtemp
from unittest.mock import patch, MagicMock, call

from elasticsearch_dsl import Search
from es_translator.interpreters import Apertium
from es_translator.es_translator import EsTranslator


class EsTranslatorTestCase(unittest.TestCase):

    def setUp(self):
        options = {
            'url': 'http://localhost:9200',
            'index': 'test_index',
            'source_language': 'fr',
            'target_language': 'en',
            'intermediary_language': None,
            'source_field': 'content',
            'target_field': 'content_translated',
            'query_string': 'test',
            'data_dir': mkdtemp(),
            'scan_scroll': '5m',
            'dry_run': False,
            'pool_size': 4,
            'pool_timeout': 10,
            'throttle': 0.5,
            'progressbar': True,
            'interpreter': 'apertium',
            'plan': False
        }
        self.translator = EsTranslator(options)

    def test_configure_search(self):
        search = self.translator.configure_search()

        self.assertIsInstance(search, Search)
        self.assertEqual(search._params['scroll'], '5m')
        self.assertEqual(search._params['size'], 4)

    def test_instantiate_interpreter(self):
        self.assertFalse(hasattr(self.translator, 'interpreter'))
        interpreter = self.translator.instantiate_interpreter()
        self.assertIsInstance(interpreter, Apertium)
        self.assertIs(self.translator.interpreter, interpreter)

    def test_search(self):
        search = self.translator.search()
        self.assertIsInstance(search, Search)
        self.assertIn('test_index', search._index)

    def test_start(self):
        self.translator.instantiate_interpreter = MagicMock()
        self.translator.search = MagicMock()
        self.translator.configure_search = MagicMock(return_value=MagicMock())
        self.translator.create_translation_queue = MagicMock()
        self.translator.with_shared_fatal_error = MagicMock()
        self.translator.translate_documents_in_pool = MagicMock()

        self.translator.start()

        self.assertTrue(self.translator.instantiate_interpreter.called)
        self.assertTrue(self.translator.search.called)
        self.assertTrue(self.translator.configure_search.called)
        self.assertTrue(self.translator.create_translation_queue.called)
        self.assertTrue(self.translator.with_shared_fatal_error.called)
        self.assertTrue(self.translator.translate_documents_in_pool.called)

    def test_start_later(self):
        self.translator.instantiate_interpreter = MagicMock()
        self.translator.search = MagicMock()
        self.translator.configure_search = MagicMock(return_value=MagicMock())
        translate_document_task = MagicMock()

        with patch('es_translator.tasks.translate_document_task.delay', translate_document_task) as mock_delay:
            self.translator.start_later()
            search_results = self.translator.search.return_value.scan.return_value
            expected_calls = [
                call(
                    self.translator.options,
                    hit.meta.to_dict()) for hit in search_results]
            mock_delay.assert_has_calls(expected_calls)
            self.assertEqual(mock_delay.call_count, len(search_results))
