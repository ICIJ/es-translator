"""Abstract base class for translation interpreters.

This module defines the interface that all translation interpreters must implement.
"""

from abc import ABC, abstractmethod
from os.path import abspath
from typing import Optional

from ..alpha import to_alpha_2, to_alpha_3, to_name


class AbstractInterpreter(ABC):
    """Abstract base class for translation interpreters.

    This class defines the interface for all translation interpreters.
    Subclasses must implement the translate() method.

    Attributes:
        name: Class-level identifier for the interpreter type.
        source: Source language code.
        target: Target language code.
        intermediary: Optional intermediary language for indirect translation.
        pack_dir: Directory for storing language packs.
    """

    name: str = 'ABSTRACT'

    def __init__(
        self,
        source: Optional[str] = None,
        target: Optional[str] = None,
        intermediary: Optional[str] = None,
        pack_dir: Optional[str] = None,
    ) -> None:
        """Initialize the interpreter.

        Args:
            source: Source language code.
            target: Target language code.
            intermediary: Optional intermediary language for indirect translation.
            pack_dir: Directory for storing language packs.
        """
        self.source = source
        self.target = target
        self.intermediary = intermediary
        # Create a temporary pack dir (if needed) to download language packs
        if pack_dir is not None:
            self.pack_dir = abspath(pack_dir)

    @property
    def name(self) -> str:
        """Get the interpreter name.

        Returns:
            The interpreter class name identifier.
        """
        return self.__class__.name

    @property
    def source_alpha_2(self) -> str:
        """Get the source language in ISO 639-1 format.

        Returns:
            2-letter language code.
        """
        return to_alpha_2(self.source)

    @property
    def source_alpha_3(self) -> str:
        """Get the source language in ISO 639-3 format.

        Returns:
            3-letter language code.
        """
        return to_alpha_3(self.source)

    @property
    def source_name(self) -> str:
        """Get the full source language name.

        Returns:
            Full language name.
        """
        return to_name(self.source_alpha_2)

    @property
    def target_alpha_2(self) -> str:
        """Get the target language in ISO 639-1 format.

        Returns:
            2-letter language code.
        """
        return to_alpha_2(self.target)

    @property
    def target_alpha_3(self) -> str:
        """Get the target language in ISO 639-3 format.

        Returns:
            3-letter language code.
        """
        return to_alpha_3(self.target)

    @property
    def intermediary_alpha_3(self) -> str:
        """Get the intermediary language in ISO 639-3 format.

        Returns:
            3-letter language code.
        """
        return to_alpha_3(self.intermediary)

    @property
    def target_name(self) -> str:
        """Get the full target language name.

        Returns:
            Full language name.
        """
        return to_name(self.target_alpha_2)

    @property
    def pair(self) -> str:
        """Get the language pair string.

        Returns:
            Language pair in format 'source-target'.
        """
        return f'{self.source}-{self.target}'

    @property
    def pair_alpha_3(self) -> str:
        """Get the language pair in ISO 639-3 format.

        Returns:
            Language pair with 3-letter codes.
        """
        return f'{self.source_alpha_3}-{self.target_alpha_3}'

    @property
    def pair_inverse(self) -> str:
        """Get the inverse language pair.

        Returns:
            Language pair in format 'target-source'.
        """
        return f'{self.target}-{self.source}'

    @property
    def has_pair(self) -> bool:
        """Check if both source and target languages are set.

        Returns:
            True if both languages are defined.
        """
        return self.source is not None and self.target is not None

    @abstractmethod
    def translate(self, text_input: str) -> str:
        """Translate text from source to target language.

        Args:
            text_input: Text to translate.

        Returns:
            Translated text.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError
