from deb_pkg_tools.control import deb822_from_string
from fileinput import FileInput
from functools import lru_cache
from glob import glob
from os.path import basename, join, isfile, dirname, abspath
from sh import dpkg_deb, mkdir, pushd, cp, rm
from urllib import request
# Module from the same package
from es_translator.alpha import to_alpha_2, to_alpha_3, to_alpha_3_pair
from es_translator.logger import logger
from es_translator.symlink import create_symlink

REPOSITORY_URL = "https://apertium.projectjj.com/apt/nightly"
PACKAGES_FILE_URL = "%s/dists/focal/main/binary-amd64/Packages" % REPOSITORY_URL

class ApertiumRepository:
    def __init__(self, cache_dir = None):
        # Create a temporary pack dir (if needed)
        self.cache_dir = abspath(cache_dir)

    @property
    @lru_cache()
    def control_file_content(self):
        response = request.urlopen(PACKAGES_FILE_URL)
        data = response.read()
        return data.decode('utf-8')

    @property
    @lru_cache()
    def packages(self):
        isnt_empty = lambda c: c is not None and c != ''
        control_strings = self.control_file_content.split('\n\n')
        control_strings = list(filter(isnt_empty, control_strings))
        return list(map(deb822_from_string, control_strings))

    @property
    @lru_cache()
    def pair_packages(self):
        return list(filter(self.is_apertium_pair, self.packages))

    def find_package(self, package):
        is_package = lambda c: c.get('Package') == package or c.get('Provides') == package
        try:
            return next(filter(is_package, self.packages))
        except StopIteration:
            logger.warning('Unable to found package %s' % package)
            return None

    def find_pair_package(self, pair):
        pair = to_alpha_3_pair(pair)
        pair_inversed = '-'.join(pair.split('-')[::-1])
        def is_pair(c):
            return c.get('Package',  '').endswith(pair) \
                or c.get('Package',  '').endswith(pair_inversed)
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

    def download_package(self, name, force = False):
        package = self.find_package(name)
        package_url = REPOSITORY_URL + '/' + package['Filename']
        package_dir = join(self.cache_dir, name)
        package_file = join(package_dir, 'package') + '.deb'
        mkdir('-p', package_dir)
        # Don't download the file twice
        if force or not isfile(package_file):
            logger.info('Downloading package %s' % name)
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

    def extract_pair_package(self, file, extraction_dir = '.'):
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
        [source, target] = basename(package_dir).split('apertium-')[-1].split('-')
        if len(source) == 2:
            aliases = (to_alpha_3(source), to_alpha_3(target))
        else:
            aliases = (to_alpha_2(source), to_alpha_2(target))
        # Build the alias dir using the alias
        alias_dir = join(extraction_dir, 'apertium-%s-%s' % aliases)
        mode_file = join(extraction_dir, 'modes', '%s-%s.mode' % (source, target))
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
        self.import_modes(clear = False)
        return package_dir

    def clear_modes(self):
        with pushd(self.cache_dir):
            rm('-Rf', 'modes')

    def import_modes(self, clear = True):
        with pushd(self.cache_dir):
            mkdir('-p', 'modes')
            # Copy all the mode files
            cp(glob('./*/modes/*.mode'), './modes')
