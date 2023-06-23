import tempfile

from argostranslate import package as argospackage
from argostranslate import translate as argostranslate
from pathlib import Path
from filelock import FileLock, Timeout

from ..abstract import AbstractInterpreter
from ...logger import logger


class ArgosPairNotAvailable(Exception):
    """
    Exception raised when the necessary language pair is not available for download.
    """


class ArgosPackageDownloadLockTimeout(Exception):
    """
    Exception raised when the necessary language cannot be downloaded after a lock reach its timeout.
    """


class Argos(AbstractInterpreter):
    """
    Argos is a class that extends the AbstractInterpreter.

    This class is responsible for handling translation tasks, specifically using the Argos interpreter.

    Attributes:
        name (str): The name of the interpreter.
    """
    name = 'ARGOS'

    def __init__(
            self,
            source=None,
            target=None,
            intermediary=None,
            pack_dir=None):
        """
        Initializes the Argos interpreter with source and target language codes.

        The function also checks if the necessary language pair is available, and downloads it if necessary.

        Args:
            source (str): The source language code.
            target (str): The target language code.
            intermediary (str, optional): The intermediary language code. Defaults to None.
            pack_dir (str, optional): The directory of language packs. This option will be ignored. Defaults to None.

        Raises:
            Exception: If the necessary language pair is not available and cannot be downloaded.
        """
        super().__init__(source, target)
        # Raise an exception if an intermediary language is provded
        if intermediary is not None:
            logger.warn(
                'Argos interpreter doesnt support intermediary language')
        if pack_dir is not None:
            logger.warn(
                'Argos interpreter doesnt support custom pack directory')
        # Raise an exception if the language pair is unkown
        if not self.is_pair_available and self.has_pair:
            try:
                self.download_necessary_languages()
            except ArgosPairNotAvailable:
                raise Exception('The pair %s is not available' % self.pair)
        else:
            logger.info('Existing package(s) found for pair %s' % self.pair)

    @property
    def is_pair_available(self):
        """
        Checks if the necessary language pair is available in the installed packages.

        Returns:
            bool: True if the language pair is available, False otherwise.
        """
        for package in argospackage.get_installed_packages():
            if package.from_code == self.source_alpha_2 and package.to_code == self.target_alpha_2:
                return True
        return False

    @property
    def local_languages(self):
        """
        Gets the codes for the installed languages.

        This method retrieves the installed languages and returns their codes as a list.
        If an AttributeError is encountered, it returns an empty list.

        Returns:
            list of str: The codes for the installed languages.
        """
        try:
            installed_languages = argostranslate.get_installed_languages()
            return [lang.code for lang in installed_languages]
        except AttributeError:
            return []

    @property
    def local_languages(self):
        """
        Gets the codes for the installed languages.

        This method retrieves the installed languages and returns their codes as a list.
        If an AttributeError is encountered, it returns an empty list.

        Returns:
            list of str: The codes for the installed languages.
        """
        try:
            installed_languages = argostranslate.get_installed_languages()
            return [lang.code for lang in installed_languages]
        except AttributeError:
            return []

    def update_package_index(self):
        """
        Updates the package index.
        """
        argospackage.update_package_index()

    def find_necessary_package(self):
        """
        Finds the necessary language package.

        This method loops over the available packages to find the necessary package based on the source and target language codes.
        If the package cannot be found, it raises an ArgosPairNotAvailable exception.

        Returns:
            Package: The necessary language package.

        Raises:
            ArgosPairNotAvailable: If the necessary language package could not be found.
        """
        for package in argospackage.get_available_packages():
            if package.from_code == self.source_alpha_2 and package.to_code == self.target_alpha_2:
                return package
        raise ArgosPairNotAvailable

    def is_package_installed(self, package):
        """
        Checks if a package is installed.

        Args:
            package (Package): The package to check.

        Returns:
            bool: True if the package is installed, False otherwise.
        """
        return package in argospackage.get_installed_packages()

    def download_and_install_package(self, package):
        """
        Downloads and installs a language package.

        This method locks the download using a file lock based on the package's source and target language codes.
        If the package is not installed, it is downloaded and installed.

        Args:
            package (Package): The package to download and install.

        Raises:
            Timeout: If a lock on the download path cannot be acquired within the timeout duration.
        """
        try:
            temp_dir = Path(tempfile.gettempdir())
            lock_path = temp_dir / f'{package.from_code}_{package.to_code}.lock'
            
            with FileLock(lock_path, timeout=600).acquire(timeout=600):
                if self.is_package_installed(package):
                    return
                download_path = package.download()
                logger.info(f'Installing Argos package {package}')
                return argospackage.install_from_path(download_path)
        except Timeout:
            raise ArgosPackageDownloadLockTimeout(
                f'Another instance of the program is downloading the package {package}. Please try again later.')

    def download_necessary_languages(self):
        """
        Downloads necessary language packages if they are not installed already.

        This method performs the following steps:
        1. Updates the package index.
        2. Finds the necessary package.
        3. Downloads and installs the package.

        Raises:
            ArgosPairNotAvailable: If the necessary language package could not be found.
            Timeout: If a lock on the download path cannot be acquired within the timeout duration.
        """
        self.update_package_index()
        necessary_package = self.find_necessary_package()
        self.download_and_install_package(necessary_package)

    @property
    def translation(self):
        """
        Returns a Translation object for the source and target languages.

        Raises:
            Exception: If either the source or target language is not installed.

        Returns:
            Translation: The Translation object for the source and target languages.
        """
        installed_languages = argostranslate.get_installed_languages()
        source = list(
            filter(
                lambda x: x.code == self.source_alpha_2,
                installed_languages))[0]
        target = list(
            filter(
                lambda x: x.code == self.target_alpha_2,
                installed_languages))[0]
        return source.get_translation(target)

    def translate(self, input):
        """
        Translates the input text from the source language to the target language.

        Args:
            input (str): The input text in the source language.

        Returns:
            str: The translated text in the target language.
        """
        return self.translation.translate(input)
