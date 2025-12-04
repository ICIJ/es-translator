import os
import unittest
from os.path import dirname
from tempfile import mkdtemp
from unittest import TestCase
from unittest.mock import patch

from es_translator.interpreters.apertium import Apertium, ApertiumNotInstalledError
from es_translator.interpreters.apertium.pairs import Pairs


def is_apertium_installed():
    """Check if Apertium is installed on the system."""
    try:
        from es_translator.interpreters.apertium.apertium import _get_apertium
        _get_apertium()
        return True
    except ApertiumNotInstalledError:
        return False


def here():
    return os.path.dirname(os.path.abspath(__file__))
def root(x):
    return os.path.abspath(os.path.join(here(), '../../../', x))
# Use the .cache dir if it exists, or use a temporary dir
pack_dir = root('.cache/APERTIUM') if os.path.isdir(root('.cache')) else mkdtemp()


@unittest.skipUnless(is_apertium_installed(), "Apertium not installed")
class TestPair(TestCase):
    @classmethod
    def setUpClass(self):
        self.por2fra = Apertium(source = 'por', target = 'fra', intermediary = None, pack_dir = pack_dir)

    def test_por2fra_pair_is_avalaible_locally(self):
        pairs = Pairs(data_dir = pack_dir, local = True)
        self.assertIn('por-fra', pairs.local_pairs)

    def test_por2fra_pair_is_avalaible_remotly(self):
        pairs = Pairs(data_dir = pack_dir, local = True)
        self.assertIn('por-fra', pairs.remote_pairs)

    def test_por2fra_pair_isnt_avalaible_locally(self):
        pairs = Pairs(data_dir = mkdtemp(),local = True)
        self.assertNotIn('por-fra', pairs.local_pairs)

    def test_jap2cos_pair_isnt_avalaible_remotly(self):
        pairs = Pairs(data_dir = pack_dir,local = True)
        self.assertNotIn('jap-cos', pairs.local_pairs)

    @patch('builtins.print')
    def test_print_only_local_pairs(self, mock_print):
        pairs = Pairs(data_dir = pack_dir, local = True)
        pairs.print_pairs()
        mock_print.assert_called_with('\n'.join(pairs.local_pairs))

    @patch('builtins.print')
    def test_print_only_remote_pairs(self, mock_print):
        pairs = Pairs(data_dir = pack_dir, local = False)
        pairs.print_pairs()
        mock_print.assert_called_with('\n'.join(pairs.remote_pairs))
