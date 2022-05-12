import os
from os.path import dirname
from unittest import TestCase
from unittest.mock import patch
from tempfile import mkdtemp
from es_translator.interpreters.apertium import Apertium
from es_translator.interpreters.apertium.pairs import Pairs


here = lambda: os.path.dirname(os.path.abspath(__file__))
root = lambda x: os.path.abspath(os.path.join(here(), '../../../', x))
# Use the .cache dir if it exists, or use a temporary dir
pack_dir = root('.cache/APERTIUM') if os.path.isdir(root('.cache')) else mkdtemp()

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
