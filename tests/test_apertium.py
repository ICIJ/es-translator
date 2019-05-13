import os
from os.path import dirname

from unittest import  TestCase
from tempfile import mkdtemp
from es_translator.apertium import Apertium

root = lambda x: os.path.join(os.path.abspath(dirname(dirname(__file__))), x)
# Use the .cache dir if it exists, or use a temporary dir
pack_dir = root('.cache') if os.path.isdir(root('.cache')) else mkdtemp()

class TestApertium(TestCase):
    @classmethod
    def setUpClass(self):
        self.en2es = Apertium('en', 'es', None, pack_dir)
        self.es2en = Apertium('es', 'en', None, pack_dir)
        self.pt2en = Apertium('pt', 'en', 'es', pack_dir)

    def test_pair_directory_is_created(self):
        self.assertIn('apertium-%s' % self.en2es.pair_package, os.listdir(pack_dir))
        self.assertIn('apertium-%s' % self.es2en.pair_package, os.listdir(pack_dir))

    def test_intermediary_pair_directory_is_created(self):
        self.assertIn('apertium-%s' % self.pt2en.intermediary_source_pair_package, os.listdir(pack_dir))

    def test_pair_packages_list(self):
        self.assertTrue(all(len(p.split('-')) == 2 for p in self.en2es.pair_packages()))

    def test_source_properties(self):
        self.assertEqual(self.en2es.source, 'en')
        self.assertEqual(self.en2es.source_alpha_2, 'en')
        self.assertEqual(self.en2es.source_alpha_3, 'eng')

    def test_target_properties(self):
        self.assertEqual(self.en2es.target, 'es')
        self.assertEqual(self.en2es.target_alpha_2, 'es')
        self.assertEqual(self.en2es.target_alpha_3, 'spa')

    def test_source_names(self):
        self.assertEqual(self.en2es.source_name, 'English')

    def test_target_names(self):
        self.assertEqual(self.en2es.target_name, 'Spanish')

    def test_translate_simple_word(self):
        self.assertEqual(self.es2en.translate('hello sir'), 'SPANISH')
