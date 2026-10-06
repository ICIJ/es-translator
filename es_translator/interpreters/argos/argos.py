"""Argos interpreter for translation operations.

This module provides the Argos interpreter class that interfaces with the
argostranslate library for neural machine translation between languages.

Note: argostranslate imports are deferred to allow setting ARGOS_DEVICE_TYPE
environment variable before the library reads its configuration.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout

from ...config import DEFAULT_ARGOS_BATCH_SIZE, DEFAULT_DEVICE
from ...logger import logger
from ..abstract import AbstractInterpreter

# argostranslate logs one INFO line per sentence split, which floods worker logs.
# A filter, not setLevel: argostranslate.utils resets its own level to INFO when imported,
# and this module imports it lazily, so any level set here would be overwritten.
logging.getLogger('argostranslate.utils').addFilter(lambda record: record.levelno > logging.INFO)


def _configure_device(device: str) -> str:
    """Configure the device for Argos translation.

    Args:
        device: Device type ('cpu', 'cuda', or 'auto').
            'auto' will use CUDA if available, otherwise CPU.

    Returns:
        The actual device configured ('cpu' or 'cuda').
    """
    if device == 'auto':
        try:
            import torch

            actual_device = 'cuda' if torch.cuda.is_available() else 'cpu'
        except ImportError:
            actual_device = 'cpu'
    else:
        actual_device = device

    # Set both env var and settings directly
    os.environ['ARGOS_DEVICE_TYPE'] = actual_device
    settings = _get_argos_settings()
    settings.device = actual_device
    return actual_device


def _get_argos_package():
    """Lazy import of argostranslate.package."""
    from argostranslate import package

    return package


def _get_argos_translate():
    """Lazy import of argostranslate.translate."""
    from argostranslate import translate

    return translate


def _get_argos_settings():
    """Lazy import of argostranslate.settings."""
    from argostranslate import settings

    return settings


def _load_translator(package_translation: Any) -> Any:
    """Load the CTranslate2 model the same way argostranslate does, once per package."""
    if package_translation.translator is None:
        import ctranslate2

        settings = _get_argos_settings()
        package_translation.translator = ctranslate2.Translator(
            str(package_translation.pkg.package_path / 'model'),
            device=settings.device,
            inter_threads=settings.inter_threads,
            intra_threads=settings.intra_threads,
            compute_type=settings.compute_type,
        )
    return package_translation.translator


def _tokenize_paragraphs(package_translation: Any, paragraphs: list[str]) -> tuple[list[int], list[list[str]]]:
    paragraph_indexes = []
    tokenized_sentences = []
    for paragraph_index, paragraph in enumerate(paragraphs):
        for sentence in package_translation.sentencizer.split_sentences(paragraph):
            paragraph_indexes.append(paragraph_index)
            tokenized_sentences.append(package_translation.pkg.tokenizer.encode(sentence))
    return paragraph_indexes, tokenized_sentences


def _translate_tokenized_sentences(package_translation: Any, tokenized_sentences: list[list[str]]) -> list[Any]:
    """Use argostranslate's options, except a token budget large enough to batch many lines together."""
    target_prefix = package_translation.pkg.target_prefix
    return _load_translator(package_translation).translate_batch(
        tokenized_sentences,
        target_prefix=[[target_prefix]] * len(tokenized_sentences) if target_prefix else None,
        replace_unknowns=True,
        max_batch_size=DEFAULT_ARGOS_BATCH_SIZE,
        batch_type='tokens',
        beam_size=max(1, _get_argos_settings().beam_size),
        num_hypotheses=1,
        length_penalty=0.2,
    )


def _decode_paragraph(package: Any, tokens: list[str]) -> str:
    value = package.tokenizer.decode(tokens)
    if package.target_prefix and value.startswith(package.target_prefix):
        value = value[len(package.target_prefix) :]
    return value.removeprefix(' ')


def _translate_paragraphs_in_one_batch(package_translation: Any, text: str) -> str:
    """Translate every line of the text in one batch.

    argostranslate translates line by line, one model call per line, which leaves the GPU idle
    on documents made of many short lines (chat logs). Batching lines together is much faster.
    """
    paragraphs = text.split('\n')
    paragraph_indexes, tokenized_sentences = _tokenize_paragraphs(package_translation, paragraphs)
    results = _translate_tokenized_sentences(package_translation, tokenized_sentences)
    tokens_by_paragraph = [[] for _ in paragraphs]
    for paragraph_index, result in zip(paragraph_indexes, results, strict=True):
        tokens_by_paragraph[paragraph_index].extend(result.hypotheses[0])
    translated_paragraphs = [_decode_paragraph(package_translation.pkg, tokens) for tokens in tokens_by_paragraph]
    return '\n'.join(translated_paragraphs).lstrip('\n')


class ArgosPairNotAvailable(Exception):
    """Exception raised when the necessary language pair is not available for download."""


class ArgosPackageDownloadLockTimeout(Exception):
    """Exception raised when the necessary language cannot be downloaded after a lock reaches its timeout."""


class Argos(AbstractInterpreter):
    """Argos translation interpreter using argostranslate.

    This class handles translation tasks using the Argos neural machine
    translation engine. Note that Argos does not support intermediary
    languages or custom package directories.

    Attributes:
        name: Identifier for this interpreter ('ARGOS').
    """

    name = 'ARGOS'

    def __init__(
        self,
        source: str | None = None,
        target: str | None = None,
        intermediary: str | None = None,
        pack_dir: str | None = None,
        device: str | None = None,
    ) -> None:
        """Initialize the Argos interpreter.

        Args:
            source: Source language code.
            target: Target language code.
            intermediary: Intermediary language code (not supported, will warn if provided).
            pack_dir: Directory for language packs (not supported, will warn if provided).
            device: Device for translation ('cpu', 'cuda', or 'auto'). Defaults to config value.

        Raises:
            Exception: If the necessary language pair is not available.
        """
        super().__init__(source, target)
        # Configure device BEFORE any argostranslate imports
        self._device_preference = device or DEFAULT_DEVICE
        self._device_configured = False
        # Raise an exception if an intermediary language is provided
        if intermediary is not None:
            logger.warning('Argos interpreter does not support intermediary language')
        if pack_dir is not None:
            logger.warning('Argos interpreter does not support custom pack directory')
        # Check pair availability - this will trigger argostranslate import
        # so we configure device first
        self._ensure_device_configured()
        if not self.is_pair_available and self.has_pair:
            try:
                self.download_necessary_languages()
            except ArgosPairNotAvailable:
                raise Exception(f'The pair {self.pair} is not available')
        else:
            logger.info(f'Existing package(s) found for pair {self.pair}')

    def _ensure_device_configured(self) -> None:
        """Configure device before argostranslate imports.

        Sets ARGOS_DEVICE_TYPE env var and argostranslate settings.device.
        """
        if not self._device_configured:
            self.device = _configure_device(self._device_preference)
            logger.info(f'Argos using device: {self.device}')
            self._device_configured = True

    @property
    def is_pair_available(self) -> bool:
        """Check if the necessary language pair is available in installed packages.

        Returns:
            True if the language pair is available, False otherwise.
        """
        argospackage = _get_argos_package()
        for package in argospackage.get_installed_packages():
            if package.from_code == self.source_alpha_2 and package.to_code == self.target_alpha_2:
                return True
        return False

    @property
    def local_languages(self) -> list[str]:
        """Get the codes for the installed languages.

        Returns:
            List of installed language codes. Returns empty list if languages cannot be retrieved.
        """
        try:
            argostranslate = _get_argos_translate()
            installed_languages = argostranslate.get_installed_languages()
            return [lang.code for lang in installed_languages]
        except AttributeError:
            return []

    def update_package_index(self) -> None:
        """Update the Argos package index to fetch latest available packages."""
        argospackage = _get_argos_package()
        argospackage.update_package_index()

    def find_necessary_package(self) -> Any:
        """Find the necessary language package.

        Searches available packages for one matching the source and target languages.

        Returns:
            The necessary language package object.

        Raises:
            ArgosPairNotAvailable: If the necessary language package could not be found.
        """
        argospackage = _get_argos_package()
        for package in argospackage.get_available_packages():
            if package.from_code == self.source_alpha_2 and package.to_code == self.target_alpha_2:
                return package
        raise ArgosPairNotAvailable

    def is_package_installed(self, package: Any) -> bool:
        """Check if a package is installed.

        Args:
            package: The package to check.

        Returns:
            True if the package is installed, False otherwise.
        """
        argospackage = _get_argos_package()
        return package in argospackage.get_installed_packages()

    def download_and_install_package(self, package: Any) -> Any | None:
        """Download and install a language package.

        Uses file locking to prevent concurrent downloads of the same package.
        Skips installation if the package is already installed.

        Args:
            package: The package to download and install.

        Returns:
            Installation result or None if package was already installed.

        Raises:
            ArgosPackageDownloadLockTimeout: If lock cannot be acquired within timeout.
        """
        argospackage = _get_argos_package()
        try:
            temp_dir = Path(tempfile.gettempdir())
            lock_path = temp_dir / f'{package.from_code}_{package.to_code}.lock'

            with FileLock(lock_path, timeout=600).acquire(timeout=600):
                if self.is_package_installed(package):
                    return None
                download_path = package.download()
                logger.info(f'Installing Argos package {package}')
                return argospackage.install_from_path(download_path)
        except Timeout as exc:
            raise ArgosPackageDownloadLockTimeout(
                f'Another instance of the program is downloading the package {package}. Please try again later.'
            ) from exc

    def download_necessary_languages(self) -> None:
        """Download necessary language packages if not installed.

        Steps:
        1. Updates the package index.
        2. Finds the necessary package.
        3. Downloads and installs the package.

        Raises:
            ArgosPairNotAvailable: If the necessary language package could not be found.
            ArgosPackageDownloadLockTimeout: If lock cannot be acquired within timeout.
        """
        self.update_package_index()
        necessary_package = self.find_necessary_package()
        self.download_and_install_package(necessary_package)

    @property
    def translation(self) -> Any:
        """Get Translation object for the source and target languages.

        Returns:
            Translation object configured for source to target language.

        Raises:
            IndexError: If either the source or target language is not installed.
        """
        argostranslate = _get_argos_translate()
        installed_languages = argostranslate.get_installed_languages()
        source = list(filter(lambda x: x.code == self.source_alpha_2, installed_languages))[0]
        target = list(filter(lambda x: x.code == self.target_alpha_2, installed_languages))[0]
        return source.get_translation(target)

    def translate(self, text_input: str) -> str:
        """Translate input text from source language to target language.

        Args:
            text_input: The input text in the source language.

        Returns:
            The translated text in the target language.
        """
        # Always configure device before translation (needed for multiprocessing workers)
        self._ensure_device_configured()
        translation = self.translation
        underlying = getattr(translation, 'underlying', None)
        if not isinstance(underlying, _get_argos_translate().PackageTranslation):
            return translation.translate(text_input)
        return _translate_paragraphs_in_one_batch(underlying, text_input)
