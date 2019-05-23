from deb_pkg_tools.control import deb822_from_string
from es_translator.logger import logger
from fileinput import FileInput
from functools import lru_cache
from glob import glob
from os.path import basename, join, isfile, dirname, abspath
from sh import dpkg_deb, mkdir, pushd, cp, rm, sed
from urllib import request

REPOSITORY_URL = "https://apertium.projectjj.com/apt/release"
PACKAGES_FILE_URL = "%s/dists/bionic/main/binary-amd64/Packages" % REPOSITORY_URL

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
        is_package = lambda c: c['Package'] == package
        try:
            return next(filter(is_package, self.packages))
        except StopIteration:
            logger.warning('Unable to found package %s' % package)
            return None

    def find_pair_package(self, pair):
        pair_inversed = '-'.join(pair.split('-')[::-1])
        is_pair = lambda c: c['Package'].endswith(pair) or c['Package'].endswith(pair_inversed)
        try:
            return next(filter(is_pair, self.pair_packages))
        except StopIteration:
            logger.warning('Unable to found pair package %s' % pair)
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
        return self.download_package(pair_package['Package'])

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

    def install_pair_package(self, pair):
        logger.info('Installing pair package %s' % pair)
        package_file = self.download_pair_package(pair)
        package_dir = self.extract_pair_package(package_file)
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
