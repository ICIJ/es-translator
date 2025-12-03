"""Unit tests for alpha.py language code utilities."""
import unittest

from es_translator.alpha import (
    InvalidLanguageCode,
    to_alpha_2,
    to_alpha_3,
    to_alpha_3_pair,
    to_name,
)


class TestAlpha(unittest.TestCase):
    """Test cases for language code conversion functions."""

    def test_to_alpha_2_from_alpha_3(self):
        """Test converting 3-letter code to 2-letter code."""
        self.assertEqual(to_alpha_2('eng'), 'en')
        self.assertEqual(to_alpha_2('fra'), 'fr')
        self.assertEqual(to_alpha_2('spa'), 'es')
        self.assertEqual(to_alpha_2('deu'), 'de')

    def test_to_alpha_2_passthrough(self):
        """Test that 2-letter codes pass through unchanged."""
        self.assertEqual(to_alpha_2('en'), 'en')
        self.assertEqual(to_alpha_2('fr'), 'fr')

    def test_to_alpha_2_invalid_code(self):
        """Test that invalid 3-letter codes raise InvalidLanguageCode."""
        with self.assertRaises(InvalidLanguageCode) as ctx:
            to_alpha_2('xyz')
        self.assertEqual(ctx.exception.code, 'xyz')

    def test_to_alpha_3_from_alpha_2(self):
        """Test converting 2-letter code to 3-letter code."""
        self.assertEqual(to_alpha_3('en'), 'eng')
        self.assertEqual(to_alpha_3('fr'), 'fra')
        self.assertEqual(to_alpha_3('es'), 'spa')
        self.assertEqual(to_alpha_3('de'), 'deu')

    def test_to_alpha_3_passthrough(self):
        """Test that 3-letter codes pass through unchanged."""
        self.assertEqual(to_alpha_3('eng'), 'eng')
        self.assertEqual(to_alpha_3('fra'), 'fra')

    def test_to_alpha_3_invalid_code(self):
        """Test that invalid 2-letter codes raise InvalidLanguageCode."""
        with self.assertRaises(InvalidLanguageCode) as ctx:
            to_alpha_3('zz')
        self.assertEqual(ctx.exception.code, 'zz')

    def test_to_name(self):
        """Test getting full language name from 2-letter code."""
        self.assertEqual(to_name('en'), 'English')
        self.assertEqual(to_name('fr'), 'French')
        self.assertEqual(to_name('es'), 'Spanish')
        self.assertEqual(to_name('de'), 'German')

    def test_to_name_invalid_code(self):
        """Test that invalid codes raise InvalidLanguageCode."""
        with self.assertRaises(InvalidLanguageCode) as ctx:
            to_name('zz')
        self.assertEqual(ctx.exception.code, 'zz')

    def test_to_alpha_3_pair(self):
        """Test converting language pair to 3-letter format."""
        self.assertEqual(to_alpha_3_pair('en-fr'), 'eng-fra')
        self.assertEqual(to_alpha_3_pair('es-de'), 'spa-deu')

    def test_to_alpha_3_pair_already_alpha_3(self):
        """Test that 3-letter pairs pass through correctly."""
        self.assertEqual(to_alpha_3_pair('eng-fra'), 'eng-fra')


if __name__ == '__main__':
    unittest.main()
