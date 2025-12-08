"""Language pairs listing for Apertium.

This module provides functionality to list available Apertium language pairs,
both locally installed and remotely available.
"""

from .apertium import Apertium


class Pairs:
    """List and display available Apertium language pairs.

    Provides access to both locally installed and remotely available
    language pairs for the Apertium translation engine.

    Attributes:
        apertium: Apertium interpreter instance.
        local: If True, prefer local pairs over remote.
    """

    def __init__(self, data_dir: str, local: bool = False) -> None:
        """Initialize the Pairs lister.

        Args:
            data_dir: Directory for Apertium language packs.
            local: If True, list local pairs; otherwise list remote pairs.
        """
        self.apertium = Apertium(pack_dir=data_dir)
        self.local = local

    @property
    def local_pairs(self) -> list[str]:
        """Get locally installed language pairs.

        Returns:
            List of locally available language pair codes.
        """
        return self.apertium.local_pairs

    @property
    def remote_pairs(self) -> list[str]:
        """Get remotely available language pairs.

        Returns:
            List of language pair codes available from the repository.
        """
        return self.apertium.remote_pairs

    @property
    def local_pairs_to_string(self) -> str:
        """Get local pairs as a newline-separated string.

        Returns:
            Newline-separated string of local pair codes.
        """
        return '\n'.join(self.local_pairs)

    @property
    def remote_pairs_to_string(self) -> str:
        """Get remote pairs as a newline-separated string.

        Returns:
            Newline-separated string of remote pair codes.
        """
        return '\n'.join(self.remote_pairs)

    def print_pairs(self) -> None:
        """Print available language pairs to stdout.

        Prints local pairs if self.local is True, otherwise prints remote pairs.
        """
        if self.local:
            print(self.local_pairs_to_string)
        else:
            print(self.remote_pairs_to_string)
