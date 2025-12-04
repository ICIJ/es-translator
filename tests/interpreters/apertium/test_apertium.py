import os
import unittest
from tempfile import mkdtemp
from unittest import TestCase

from es_translator.interpreters.apertium import Apertium, ApertiumNotInstalledError


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
class TestApertium(TestCase):
    @classmethod
    def setUpClass(self):
        self.eng2spa = Apertium(source = 'eng', target = 'spa', intermediary = None, pack_dir = pack_dir)
        self.spa2eng = Apertium(source = 'spa', target = 'eng', intermediary = None, pack_dir = pack_dir)
        self.por2eng = Apertium(source = 'por', target = 'eng', intermediary = 'cat', pack_dir = pack_dir)
        self.por2fra = Apertium(source = 'por', target = 'fra', intermediary = None, pack_dir = pack_dir)

    def test_pair_directory_is_created(self):
        self.assertIn(f'apertium-{self.eng2spa.pair_package}', os.listdir(pack_dir))
        self.assertIn(f'apertium-{self.spa2eng.pair_package}', os.listdir(pack_dir))

    def test_intermediary_pair_directory_is_created(self):
        self.assertIn(f'apertium-{self.por2eng.intermediary_source_pair_package}', os.listdir(pack_dir))

    def test_pair_packages_list(self):
        self.assertTrue(all(len(p.split('-')) == 2 for p in self.eng2spa.remote_pairs))

    def test_source_properties(self):
        self.assertEqual(self.eng2spa.source, 'eng')
        self.assertEqual(self.eng2spa.source_alpha_2, 'en')
        self.assertEqual(self.eng2spa.source_alpha_3, 'eng')

    def test_target_properties(self):
        self.assertEqual(self.eng2spa.target, 'spa')
        self.assertEqual(self.eng2spa.target_alpha_2, 'es')
        self.assertEqual(self.eng2spa.target_alpha_3, 'spa')

    def test_source_names(self):
        self.assertEqual(self.eng2spa.source_name, 'English')

    def test_target_names(self):
        self.assertEqual(self.eng2spa.target_name, 'Spanish')

    def test_translate_simple_word(self):
        self.assertEqual(self.eng2spa.translate('hello').strip(), 'hola')
        self.assertEqual(self.eng2spa.translate('hello sir').strip(), 'hola Señor')
        self.assertEqual(self.spa2eng.translate('hola').strip(), 'hello')
        self.assertEqual(self.por2eng.translate('obrigado').strip(), 'thank you')
        self.assertEqual(self.por2fra.translate('obrigado').strip(), 'merci')
