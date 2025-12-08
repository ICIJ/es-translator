"""Symlink utilities for file system operations.

This module provides helper functions for creating symbolic links.
"""

from os.path import isdir, isfile, islink

from sh import ln, rm


def create_symlink(source: str, target: str, options: str = '-s', force: bool = True) -> None:
    """Create a symbolic link from source to target.

    Args:
        source: Path to the source file or directory.
        target: Path where the symbolic link will be created.
        options: Options to pass to ln command. Defaults to '-s' for symbolic.
        force: If True, remove existing symlink at target. Defaults to True.
    """
    if isdir(source) or isfile(source):
        if force and islink(target):
            rm(target)
        ln(options, source, target)
