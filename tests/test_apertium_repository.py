import os
from os.path import dirname, isfile, isdir, basename

from unittest import  TestCase
from es_translator.apertium_repository import ApertiumRepository

root = lambda x: os.path.join(os.path.abspath(dirname(dirname(__file__))), x)
# Use the .cache dir if it exists, or use a temporary dir
cache_dir = root('.cache') if os.path.isdir(root('.cache')) else mkdtemp()

class TestApertium(TestCase):
    @classmethod
    def setUpClass(self):
        self.apr = ApertiumRepository(cache_dir = cache_dir)

    def test_has_packages_list(self):
        self.assertEqual(type(self.apr.packages), list)

    def test_find_apertium_package(self):
        self.assertTrue(self.apr.find_package('apertium') is not None)

    def test_find_apertium_enes_package(self):
        self.assertTrue(self.apr.find_package('apertium-en-es') is not None)

    def test_find_package_for_pair(self):
        self.assertTrue(self.apr.find_pair_package('en-es') is not None)

    def test_find_package_for_inversed_pair(self):
        self.assertTrue(self.apr.find_pair_package('es-en') is not None)

    def test_pair_packages(self):
        self.assertEqual(type(self.apr.pair_packages), list)

    def test_is_apertium_pair(self):
        self.assertTrue(self.apr.is_apertium_pair(dict(Package='apertium-en-es')))
        self.assertTrue(self.apr.is_apertium_pair(dict(Package='apertium-spa-cat')))
        self.assertFalse(self.apr.is_apertium_pair(dict(Package='nop-en-es')))
        self.assertFalse(self.apr.is_apertium_pair(dict(Package='en-es')))

    def test_download_package(self):
        package_file = self.apr.download_package('apertium-en-es')
        self.assertTrue(isfile(package_file))

    def test_download_pair_package(self):
        package_file = self.apr.download_pair_package('es-pt')
        self.assertTrue(isfile(package_file))

    def test_download_pair_package_inversed(self):
        package_file = self.apr.download_pair_package('pt-es')
        self.assertTrue(isfile(package_file))

    def test_extract_pair_package(self):
        package_file = self.apr.download_pair_package('en-es')
        package_directory = self.apr.extract_pair_package(package_file)
        self.assertTrue(isdir(package_directory))
        self.assertTrue(isdir(package_directory + '/modes'))
        self.assertTrue(isdir(package_directory + '/apertium-en-es'))

    def test_import_modes(self):
        self.apr.clear_modes()
        self.assertFalse(isdir(cache_dir + '/modes'))
        package_file = self.apr.download_pair_package('en-es')
        self.apr.extract_pair_package(package_file)
        self.apr.import_modes(clear = False)
        self.assertTrue(isdir(cache_dir + '/modes'))
        self.assertTrue(isfile(cache_dir + '/modes/en-es.mode'))
        self.assertTrue(isfile(cache_dir + '/modes/es-en.mode'))

    def test_install_pair_package_alpha3(self):
        self.apr.clear_modes()
        self.assertFalse(isdir(cache_dir + '/modes'))
        self.apr.install_pair_package('fra-cat')
        self.assertTrue(isdir(cache_dir + '/modes'))
        self.assertTrue(isfile(cache_dir + '/modes/fra-cat.mode'))

    def test_install_pair_package_reversed(self):
        self.apr.clear_modes()
        self.assertFalse(isdir(cache_dir + '/modes'))
        self.apr.install_pair_package('es-en')
        self.assertTrue(isdir(cache_dir + '/modes'))
        self.assertTrue(isfile(cache_dir + '/modes/en-es.mode'))
        self.assertTrue(isfile(cache_dir + '/modes/es-en.mode'))
