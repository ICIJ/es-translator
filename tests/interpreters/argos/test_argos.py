from unittest import TestCase
from unittest.mock import MagicMock, patch

from es_translator.interpreters import Argos


class TestArgos(TestCase):
    @classmethod
    def setUpClass(self):
        self.spa2eng = Argos(source = 'spa', target = 'eng')
        self.eng2spa = Argos(source = 'eng', target = 'spa')
        self.fra2eng = Argos(source='fra', target='eng')
        self.package = MagicMock()
        self.package.from_code = self.spa2eng.source_alpha_2
        self.package.to_code = self.spa2eng.target_alpha_2

    def test_has_eng_to_spa_is_supported(self):
        self.assertTrue(self.eng2spa.is_pair_available)

    def test_has_spa_to_eng_is_supported(self):
        self.assertTrue(self.spa2eng.is_pair_available)

    def test_has_fra_to_eng_is_supported(self):
        self.assertTrue(self.fra2eng.is_pair_available)

    def test_has_ava_to_kau_isnt_supported(self):
        with self.assertRaises(Exception):
            self.argos = Argos(source = 'ava', target = 'kau')

    def test_translation_from_fra_to_eng(self):
        self.assertEqual(self.fra2eng.translate("bonjour!").lower(), "hello!")

    def test_translation_from_de_to_en(self):
        self.assertEqual(self.fra2eng.translate('bonjour monsieur, comment ça va ?'), 'Hello sir, how are you?')

    def test_find_necessary_package(self):
        with patch('argostranslate.package.get_available_packages', return_value=[self.package]):
            result = self.spa2eng.find_necessary_package()
            self.assertEqual(result, self.package)

    def test_is_package_installed_true(self):
        with patch('argostranslate.package.get_installed_packages', return_value=[self.package]):
            result = self.spa2eng.is_package_installed(self.package)
            self.assertTrue(result)

    def test_is_package_installed_false(self):
        with patch('argostranslate.package.get_installed_packages', return_value=[]):
            result = self.spa2eng.is_package_installed(self.package)
            self.assertFalse(result)

    @patch('argostranslate.package.install_from_path')
    @patch.object(Argos, 'is_package_installed', return_value=False)
    def test_download_and_install_package(self, mock_is_installed, mock_install):
        self.package.download = MagicMock()
        self.spa2eng.download_and_install_package(self.package)
        self.package.download.assert_called_once()
        mock_install.assert_called_once()

    @patch.object(Argos, 'download_and_install_package')
    @patch.object(Argos, 'find_necessary_package', return_value=MagicMock())
    @patch.object(Argos, 'update_package_index')
    def test_download_necessary_languages(self, mock_update_index, mock_find_package, mock_download_install):
        self.spa2eng.download_necessary_languages()
        mock_update_index.assert_called_once()
        mock_find_package.assert_called_once()
        mock_download_install.assert_called_once()
