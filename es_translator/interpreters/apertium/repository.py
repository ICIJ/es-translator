from deb_pkg_tools.control import parse_deb822
from fileinput import FileInput
from functools import lru_cache
from glob import glob
from os.path import basename, join, isfile, dirname, abspath
from sh import dpkg_deb, mkdir, pushd, cp, rm
from urllib import request
import platform
import re
# Module from the same package
from es_translator.alpha import to_alpha_2, to_alpha_3, to_alpha_3_pair
from es_translator.logger import logger
from es_translator.symlink import create_symlink

REPOSITORY_URL = "https://apertium.projectjj.com/apt/nightly"


def get_packages_file_url(arch=None):
    """
    Get the Packages file URL for the appropriate architecture.

    Args:
        arch: Architecture string ('amd64', 'i386', etc.). If None, auto-detect.

    Returns:
        URL string for the Packages file
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
            logger.warning('Unknown architecture %s, defaulting to amd64' % machine)

    return "%s/dists/noble/main/binary-%s/Packages" % (REPOSITORY_URL, arch)


class ApertiumRepository:
    def __init__(self, cache_dir=None, arch=None):
        """
        Initialize the Apertium repository handler.

        Args:
            cache_dir: Directory for caching downloaded packages
            arch: Architecture string ('amd64', 'i386'). If None, auto-detect.
        """
        # Create a temporary pack dir (if needed)
        self.cache_dir = abspath(cache_dir)
        self.arch = arch

    @property
    def packages_file_url(self):
        """Get the Packages file URL for the configured architecture."""
        return get_packages_file_url(self.arch)

    @property
    @lru_cache()
    def control_file_content(self):
        response = request.urlopen(self.packages_file_url)
        data = response.read()
        return data.decode('utf-8')

    @property
    @lru_cache()
    def packages(self):
        def isnt_empty(c): return c is not None and c != ''
        control_strings = self.control_file_content.split('\n\n')
        control_strings = list(filter(isnt_empty, control_strings))
        return list(map(parse_deb822, control_strings))

    @property
    @lru_cache()
    def pair_packages(self):
        return list(filter(self.is_apertium_pair, self.packages))

    def find_package(self, package):
        def is_package(c): return c.get(
            'Package') == package or c.get('Provides') == package
        try:
            return next(filter(is_package, self.packages))
        except StopIteration:
            logger.warning('Unable to found package %s' % package)
            return None

    def find_pair_package(self, pair):
        pair = to_alpha_3_pair(pair)
        pair_inversed = '-'.join(pair.split('-')[::-1])

        def is_pair(c):
            return c.get('Package', '').endswith(pair) \
                or c.get('Package', '').endswith(pair_inversed)
        try:
            return next(filter(is_pair, self.pair_packages))
        except StopIteration:
            return None

    def is_apertium_pair(self, control):
        try:
            parts = control['Package'].split('-')
            return len(parts) == 3 and parts[0] == 'apertium'
        except KeyError:
            return False

    def find_latest_package_in_pool(self, package_name, filename):
        logger.info('Attempting to find latest version from pool directory')
        # Extract the pool directory path
        filename_parts = filename.split('/')
        pool_dir_url = REPOSITORY_URL + '/' + '/'.join(filename_parts[:-1]) + '/'
        # Fetch the directory listing
        response = request.urlopen(pool_dir_url)
        html_content = response.read().decode('utf-8')
        # Find all .deb files for this package
        pattern = r'href="(' + re.escape(package_name) + r'_[^"]+\.deb)"'
        matches = re.findall(pattern, html_content)
        if matches:
            # Use the last one (likely the newest)
            latest_file = matches[-1]
            package_url = pool_dir_url + latest_file
            logger.info('Found latest version: %s' % latest_file)
            return package_url
        else:
            raise Exception('Could not find package %s in pool directory' % package_name)

    def download_package(self, name, force=False):
        package = self.find_package(name)
        package_dir = join(self.cache_dir, name)
        package_file = join(package_dir, 'package') + '.deb'
        mkdir('-p', package_dir)
        # Don't download the file twice
        if force or not isfile(package_file):
            logger.info('Downloading package %s' % name)
            # Try the URL from Packages file first
            package_url = REPOSITORY_URL + '/' + package['Filename']
            try:
                request.urlretrieve(package_url, package_file)
            except Exception as e:
                # If that fails, try to find the latest version in the pool directory
                logger.warning('Failed to download from Packages file URL: %s' % str(e))
                package_url = self.find_latest_package_in_pool(name, package['Filename'])
                request.urlretrieve(package_url, package_file)
        return package_file

    def download_pair_package(self, pair):
        pair_package = self.find_pair_package(pair)
        if pair_package is not None:
            return self.download_package(pair_package.get('Package'))
        else:
            raise Exception('No pair package  available for "%s"' % pair)

    def replace_in_file(self, file, target, replacement):
        with FileInput(file, inplace=True) as fileinput:
            for line in fileinput:
                print(line.replace(target, replacement), end='')

    def extract_pair_package(self, file, extraction_dir='.'):
        workdir = dirname(file)
        with pushd(workdir):
            # Extract the file from the .deb
            dpkg_deb('-x', file, extraction_dir)
            # Copy the files we need
            cp('-rlf', glob('usr/share/apertium/*'), extraction_dir)
            # Remove everything else
            rm('-Rf', 'usr')
            # Rewrite paths in modes files
            for mode in glob('modes/*.mode'):
                self.replace_in_file(mode, '/usr/share/apertium', workdir)
        return workdir

    def create_pair_package_alias(self, package_dir):
        extraction_dir = dirname(package_dir) + '/'
        [source, target] = basename(package_dir).split(
            'apertium-')[-1].split('-')
        if len(source) == 2:
            aliases = (to_alpha_3(source), to_alpha_3(target))
        else:
            aliases = (to_alpha_2(source), to_alpha_2(target))
        # Build the alias dir using the alias
        alias_dir = join(extraction_dir, 'apertium-%s-%s' % aliases)
        mode_file = join(
            extraction_dir, 'modes', '%s-%s.mode' %
            (source, target))
        mode_alias_file = join(extraction_dir, 'modes', '%s-%s.mode' % aliases)
        # Use a symbolic links
        create_symlink(package_dir, alias_dir)
        create_symlink(mode_file, mode_alias_file)
        return alias_dir

    def install_pair_package(self, pair):
        logger.info('Installing pair package %s' % pair)
        package_file = self.download_pair_package(pair)
        package_dir = self.extract_pair_package(package_file)
        alias_dir = self.create_pair_package_alias(package_dir)
        self.import_modes(clear=False)
        return package_dir

    def clear_modes(self):
        with pushd(self.cache_dir):
            rm('-Rf', 'modes')

    def import_modes(self, clear=True):
        with pushd(self.cache_dir):
            mkdir('-p', 'modes')
            # Copy all the mode files
            cp(glob('./*/modes/*.mode'), './modes')
