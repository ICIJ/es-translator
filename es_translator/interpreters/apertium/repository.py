"""Apertium repository management module for downloading and installing translation pairs."""

import platform
import re
from fileinput import FileInput
from functools import lru_cache
from glob import glob
from os.path import abspath, basename, dirname, isfile, join
from typing import Optional
from urllib import request
from urllib.error import HTTPError, URLError

from deb_pkg_tools.control import parse_deb822
from sh import cp, dpkg_deb, mkdir, pushd, rm

# Module from the same package
from es_translator.alpha import to_alpha_2, to_alpha_3, to_alpha_3_pair
from es_translator.logger import logger
from es_translator.symlink import create_symlink

REPOSITORY_URL = "https://apertium.projectjj.com/apt/nightly"


def get_packages_file_url(arch: Optional[str] = None) -> str:
    """Get the Packages file URL for the appropriate architecture.

    Args:
        arch: Architecture string ('amd64', 'i386', etc.). If None, auto-detect.

    Returns:
        URL string for the Packages file.

    Note:
        Auto-detection defaults to 'amd64' for unknown architectures.
    """
    if arch is None:
        # Auto-detect architecture
        machine = platform.machine().lower()
        if machine in ('x86_64', 'amd64'):
            arch = 'amd64'
        elif machine in ('i386', 'i686'):
            arch = 'i386'
        else:
            # Default to amd64 for other architectures
            arch = 'amd64'
            logger.warning(f'Unknown architecture {machine}, defaulting to amd64')

    return f"{REPOSITORY_URL}/dists/noble/main/binary-{arch}/Packages"


class ApertiumRepository:
    """Manages Apertium package repository operations.

    Handles downloading, extracting, and installing Apertium translation pairs
    from the official repository.

    Attributes:
        cache_dir: Directory path for caching downloaded packages.
        arch: System architecture ('amd64', 'i386', etc.).
    """

    def __init__(self, cache_dir: Optional[str] = None, arch: Optional[str] = None):
        """Initialize the Apertium repository handler.

        Args:
            cache_dir: Directory for caching downloaded packages. Defaults to None.
            arch: Architecture string ('amd64', 'i386'). If None, auto-detect.
        """
        self.cache_dir = abspath(cache_dir) if cache_dir else abspath('.')
        self.arch = arch

    @property
    def packages_file_url(self) -> str:
        """Get the Packages file URL for the configured architecture."""
        return get_packages_file_url(self.arch)

    @property
    @lru_cache
    def control_file_content(self) -> str:
        """Fetch and cache the Packages control file content.

        Returns:
            Decoded UTF-8 content of the Packages file.

        Raises:
            URLError: If the URL cannot be accessed.
            HTTPError: If HTTP request fails.
        """
        try:
            response = request.urlopen(self.packages_file_url)
            data = response.read()
            return data.decode('utf-8')
        except (URLError, HTTPError) as e:
            logger.error(f'Failed to fetch packages file from {self.packages_file_url}: {e}')
            raise

    @property
    @lru_cache
    def packages(self) -> list[dict]:
        """Parse and cache the list of available packages.

        Returns:
            List of package metadata dictionaries.
        """
        def isnt_empty(c: str) -> bool:
            return c is not None and c != ''

        control_strings = self.control_file_content.split('\n\n')
        control_strings = list(filter(isnt_empty, control_strings))
        return list(map(parse_deb822, control_strings))

    @property
    @lru_cache
    def pair_packages(self) -> list[dict]:
        """Get filtered list of Apertium translation pair packages.

        Returns:
            List of package dictionaries that are translation pairs.
        """
        return list(filter(self.is_apertium_pair, self.packages))

    def find_package(self, package: str) -> Optional[dict]:
        """Find a package by name or provided name.

        Args:
            package: Package name to search for.

        Returns:
            Package metadata dictionary if found, None otherwise.
        """
        def is_package(c: dict) -> bool:
            return c.get('Package') == package or c.get('Provides') == package

        try:
            return next(filter(is_package, self.packages))
        except StopIteration:
            logger.warning(f'Unable to find package {package}')
            return None

    def find_pair_package(self, pair: str) -> Optional[dict]:
        """Find a translation pair package.

        Searches for both forward (source-target) and reverse (target-source) pairs.

        Args:
            pair: Language pair in format 'source-target'.

        Returns:
            Package metadata dictionary if found, None otherwise.
        """
        pair = to_alpha_3_pair(pair)
        pair_inversed = '-'.join(pair.split('-')[::-1])

        def is_pair(c: dict) -> bool:
            package_name = c.get('Package', '')
            return package_name.endswith(pair) or package_name.endswith(pair_inversed)

        try:
            return next(filter(is_pair, self.pair_packages))
        except StopIteration:
            return None

    def is_apertium_pair(self, control: dict) -> bool:
        """Check if a package is an Apertium translation pair.

        Args:
            control: Package metadata dictionary.

        Returns:
            True if package is a translation pair (format: apertium-XX-YY).
        """
        try:
            parts = control['Package'].split('-')
            return len(parts) == 3 and parts[0] == 'apertium'
        except KeyError:
            return False

    def find_latest_package_in_pool(self, package_name: str, filename: str) -> str:
        """Find latest package version from pool directory.

        Used as fallback when the Packages file lists an outdated version.

        Args:
            package_name: Name of the package to find.
            filename: Original filename from Packages file (used to determine pool directory).

        Returns:
            URL of the latest package version found.

        Raises:
            Exception: If no matching package is found in the pool directory.
            URLError: If the pool directory cannot be accessed.
        """
        logger.info('Attempting to find latest version from pool directory')

        # Extract the pool directory path
        filename_parts = filename.split('/')
        pool_dir_url = f"{REPOSITORY_URL}/{'/'.join(filename_parts[:-1])}/"

        try:
            # Fetch the directory listing
            response = request.urlopen(pool_dir_url)
            html_content = response.read().decode('utf-8')
        except (URLError, HTTPError) as e:
            logger.error(f'Failed to access pool directory {pool_dir_url}: {e}')
            raise

        # Find all .deb files for this package
        pattern = rf'href="({re.escape(package_name)}_[^"]+\.deb)"'
        matches = re.findall(pattern, html_content)

        if matches:
            # Use the last one (likely the newest based on alphabetical sorting)
            latest_file = matches[-1]
            package_url = pool_dir_url + latest_file
            logger.info(f'Found latest version: {latest_file}')
            return package_url
        else:
            raise Exception(f'Could not find package {package_name} in pool directory')

    def download_package(self, name: str, force: bool = False) -> str:
        """Download a package from the repository.

        Args:
            name: Package name to download.
            force: If True, re-download even if package already exists.

        Returns:
            Path to the downloaded .deb file.

        Raises:
            Exception: If package cannot be found or downloaded.
        """
        package = self.find_package(name)
        if package is None:
            raise Exception(f'Package {name} not found in repository')

        package_dir = join(self.cache_dir, name)
        package_file = join(package_dir, 'package.deb')
        mkdir('-p', package_dir)

        # Don't download the file twice
        if force or not isfile(package_file):
            logger.info(f'Downloading package {name}')

            # Try the URL from Packages file first
            package_url = f"{REPOSITORY_URL}/{package['Filename']}"
            try:
                request.urlretrieve(package_url, package_file)
            except Exception as e:
                # If that fails, try to find the latest version in the pool directory
                logger.warning(f'Failed to download from Packages file URL: {e}')
                package_url = self.find_latest_package_in_pool(name, package['Filename'])
                request.urlretrieve(package_url, package_file)

        return package_file

    def download_pair_package(self, pair: str) -> str:
        """Download a translation pair package.

        Args:
            pair: Language pair in format 'source-target'.

        Returns:
            Path to the downloaded .deb file.

        Raises:
            Exception: If no pair package is available for the given languages.
        """
        pair_package = self.find_pair_package(pair)
        if pair_package is not None:
            return self.download_package(pair_package.get('Package'))
        else:
            raise Exception(f'No pair package available for "{pair}"')

    def replace_in_file(self, file: str, target: str, replacement: str) -> None:
        """Replace all occurrences of target string in a file.

        Args:
            file: Path to the file to modify.
            target: String to search for.
            replacement: String to replace with.
        """
        with FileInput(file, inplace=True) as fileinput:
            for line in fileinput:
                print(line.replace(target, replacement), end='')

    def extract_pair_package(self, file: str, extraction_dir: str = '.') -> str:
        """Extract a translation pair .deb package.

        Args:
            file: Path to the .deb file to extract.
            extraction_dir: Directory to extract files into. Defaults to '.'.

        Returns:
            Path to the working directory containing extracted files.
        """
        workdir = dirname(file)
        with pushd(workdir):
            # Extract the file from the .deb
            dpkg_deb('-x', file, extraction_dir)
            # Copy the files we need
            cp('-rlf', glob('usr/share/apertium/*'), extraction_dir)
            # Remove everything else
            rm('-Rf', 'usr')
            # Rewrite paths in modes files to point to the working directory
            for mode in glob('modes/*.mode'):
                self.replace_in_file(mode, '/usr/share/apertium', workdir)
        return workdir

    def create_pair_package_alias(self, package_dir: str) -> str:
        """Create symbolic links for alternative language code formats.

        Creates aliases between ISO 639-1 (2-letter) and ISO 639-3 (3-letter) codes.

        Args:
            package_dir: Directory containing the extracted package.

        Returns:
            Path to the created alias directory.
        """
        extraction_dir = dirname(package_dir) + '/'
        source, target = basename(package_dir).split('apertium-')[-1].split('-')

        # Determine alias codes based on current format
        if len(source) == 2:
            aliases = (to_alpha_3(source), to_alpha_3(target))
        else:
            aliases = (to_alpha_2(source), to_alpha_2(target))

        # Build the alias dir using the alias codes
        alias_dir = join(extraction_dir, f'apertium-{aliases[0]}-{aliases[1]}')
        mode_file = join(extraction_dir, 'modes', f'{source}-{target}.mode')
        mode_alias_file = join(extraction_dir, 'modes', f'{aliases[0]}-{aliases[1]}.mode')

        # Use symbolic links for aliases
        create_symlink(package_dir, alias_dir)
        create_symlink(mode_file, mode_alias_file)

        return alias_dir

    def install_pair_package(self, pair: str) -> str:
        """Download, extract, and install a translation pair package.

        Args:
            pair: Language pair in format 'source-target'.

        Returns:
            Path to the installed package directory.
        """
        logger.info(f'Installing pair package {pair}')
        package_file = self.download_pair_package(pair)
        package_dir = self.extract_pair_package(package_file)
        self.create_pair_package_alias(package_dir)
        self.import_modes(clear=False)
        return package_dir

    def clear_modes(self) -> None:
        """Remove all mode files from the cache directory."""
        with pushd(self.cache_dir):
            rm('-Rf', 'modes')

    def import_modes(self, clear: bool = True) -> None:
        """Import all mode files from installed packages into the modes directory.

        Args:
            clear: If True, clear existing modes before importing. Defaults to True.
        """
        with pushd(self.cache_dir):
            if clear:
                self.clear_modes()
            mkdir('-p', 'modes')
            # Copy all the mode files from installed packages
            mode_files = glob('./*/modes/*.mode')
            if mode_files:
                cp(mode_files, './modes')
