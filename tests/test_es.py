"""Unit tests for es.py TranslatedHit class."""
import unittest
from unittest.mock import MagicMock, patch


class TestTranslatedHit(unittest.TestCase):
    """Test cases for TranslatedHit class."""

    def setUp(self):
        """Set up test fixtures."""
        # Import here to avoid import-time side effects
        from es_translator.es import TranslatedHit

        self.TranslatedHit = TranslatedHit

        # Create a mock hit object
        self.mock_hit = MagicMock()
        self.mock_hit.to_dict.return_value = {
            'content': 'Hello world',
            'content_translated': []
        }
        self.mock_hit.meta.id = 'doc123'
        self.mock_hit.meta.index = 'test_index'
        self.mock_hit.meta.to_dict.return_value = {'routing': 'route1'}
        self.mock_hit.__setitem__ = MagicMock()
        self.mock_hit.__getitem__ = MagicMock(return_value=[])

    def test_init_sets_fields(self):
        """Test that __init__ sets fields correctly."""
        hit = self.TranslatedHit(self.mock_hit, 'content', 'translated', True)
        self.assertEqual(hit.source_field, 'content')
        self.assertEqual(hit.target_field, 'translated')
        self.assertTrue(hit.force)

    def test_source_value(self):
        """Test source_value property returns source content."""
        hit = self.TranslatedHit(self.mock_hit)
        self.assertEqual(hit.source_value, 'Hello world')

    def test_translations_empty(self):
        """Test translations property returns empty list when no translations."""
        hit = self.TranslatedHit(self.mock_hit)
        self.assertEqual(hit.translations, [])

    def test_translations_with_content(self):
        """Test translations property returns existing translations."""
        self.mock_hit.to_dict.return_value = {
            'content': 'Hello',
            'content_translated': [{'content': 'Bonjour'}]
        }
        hit = self.TranslatedHit(self.mock_hit)
        self.assertEqual(len(hit.translations), 1)
        self.assertEqual(hit.translations[0]['content'], 'Bonjour')

    def test_id_property(self):
        """Test id property returns document ID."""
        hit = self.TranslatedHit(self.mock_hit)
        self.assertEqual(hit.id, 'doc123')

    def test_routing_property(self):
        """Test routing property returns routing value."""
        hit = self.TranslatedHit(self.mock_hit)
        self.assertEqual(hit.routing, 'route1')

    def test_routing_property_none(self):
        """Test routing property returns None when not set."""
        self.mock_hit.meta.to_dict.return_value = {}
        hit = self.TranslatedHit(self.mock_hit)
        self.assertIsNone(hit.routing)

    def test_index_property(self):
        """Test index property returns index name."""
        hit = self.TranslatedHit(self.mock_hit)
        self.assertEqual(hit.index, 'test_index')

    def test_body_property(self):
        """Test body property returns update body structure."""
        hit = self.TranslatedHit(self.mock_hit)
        body = hit.body
        self.assertIn('doc', body)
        self.assertIn('content_translated', body['doc'])

    def test_is_translated_false(self):
        """Test is_translated returns False when no matching translation."""
        hit = self.TranslatedHit(self.mock_hit)
        self.assertFalse(hit.is_translated('English', 'French', 'ARGOS'))

    def test_is_translated_true(self):
        """Test is_translated returns True when matching translation exists."""
        self.mock_hit.to_dict.return_value = {
            'content': 'Hello',
            'content_translated': [{
                'source_language': 'ENGLISH',
                'target_language': 'FRENCH',
                'translator': 'ARGOS',
                'content': 'Bonjour'
            }]
        }
        hit = self.TranslatedHit(self.mock_hit)
        self.assertTrue(hit.is_translated('English', 'French', 'ARGOS'))

    def test_save_calls_client_update(self):
        """Test save method calls Elasticsearch client update."""
        hit = self.TranslatedHit(self.mock_hit)
        mock_client = MagicMock()
        hit.save(mock_client)
        mock_client.update.assert_called_once_with(
            index='test_index',
            id='doc123',
            routing='route1',
            body=hit.body
        )


if __name__ == '__main__':
    unittest.main()
