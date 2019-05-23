import sys
from es_translator.apertium_repository import ApertiumRepository
from es_translator.logger import logger
from tempfile import mkdtemp, NamedTemporaryFile
from functools import lru_cache
from pycountry import languages
from os.path import join, isdir
from glob import glob
from sh import apertium, apertium_get, pushd, mkdir, cp, grep, ErrorReturnCode

class Apertium:
    def __init__(self, source, target, intermediary = None, pack_dir = None):
        self.source = source
        self.target = target
        self.intermediary = intermediary
        # Create a temporary pack dir (if needed)
        self.pack_dir = pack_dir or mkdtemp()
        # A class to download necessary pair package
        self.repository = ApertiumRepository(self.pack_dir)
        # Raise an exception if the language pair is unkown
        if not self.is_pair_available:
            try:
                self.download_necessary_pairs()
            except StopIteration:
                raise Exception('The pair is not available')
        else:
            logger.info('Existing package(s) found for pair %s' % self.pair)

    def to_alpha_2(self, code):
        if len(code) == 3:
            return languages.get(alpha_3 = code).alpha_2
        else:
            return code

    def to_alpha_3(self, code):
        if len(code) == 2:
            return languages.get(alpha_2 = code).alpha_3
        else:
            return code

    @property
    def source_alpha_2(self):
        return self.to_alpha_2(self.source)

    @property
    def source_alpha_3(self):
        return self.to_alpha_3(self.source)

    @property
    def source_name(self):
        return languages.get(alpha_2=self.source_alpha_2).name

    @property
    def target_alpha_2(self):
        return self.to_alpha_2(self.target)

    @property
    def target_alpha_3(self):
        return self.to_alpha_3(self.target)

    @property
    def target_name(self):
        return languages.get(alpha_2=self.target_alpha_2).name

    @property
    def pair(self):
        return '%s-%s' % (self.source, self.target)

    @property
    def pair_inverse(self):
        return '%s-%s' % (self.target, self.source)

    @property
    def pair_package(self):
        return self.pair_to_pair_package(self.pair)

    @property
    def is_pair_available(self):
        return not self.intermediary and self.pair in self.available_pairs

    @property
    def pairs_pipeline(self):
        if self.intermediary:
            return [self.intermediary_source_pair, self.intermediary_target_pair]
        else:
            return [self.pair]

    @property
    def intermediary_source_pair(self):
        return '%s-%s' % (self.source, self.intermediary)

    @property
    def intermediary_source_pair_package(self):
        return self.pair_to_pair_package(self.intermediary_source_pair)

    @property
    def intermediary_target_pair(self):
        return '%s-%s' % (self.intermediary, self.target)

    @property
    def intermediary_target_pair_package(self):
        return self.pair_to_pair_package(self.intermediary_target_pair)

    @property
    def intermediary_pairs(self):
        # Find the intermediary lang only if not given
        if self.intermediary is None:
            trunk_packages = [ s.split('-') for s in self.pair_packages() ]
            # Build a tree of languages and their children
            packages_tree = self.lang_tree(self.source, trunk_packages)
            # Find the first path between self.source (the root) and self.target in the given tree
            self.intermediary = self.first_pairs_path(packages_tree, self.target)[0]
        # We build the two intermediary pairs
        return [ self.intermediary_source_pair, self.intermediary_target_pair ]

    @property
    def available_pairs(self):
        output = apertium('-d', self.pack_dir, '-l').strip()
        return [ s.strip() for s in output.split('\n') ]

    @lru_cache()
    def pair_packages(self, module = 'trunk'):
        lists = apertium_get('-l', module) if module is not None else apertium_get('-l')
        return [ s.strip() for s in grep(lists, '-').strip().split('\n') ]

    def pair_to_pair_package(self, pair):
        pair_parts = pair.split('-')
        combinations = []
        combinations.append('%s-%s' % (pair_parts[0], pair_parts[1]))
        combinations.append('%s-%s' % (pair_parts[1], pair_parts[0]))
        try:
            return next(p for p in self.pair_packages() if p in combinations)
        except StopIteration:
            return None

    def download_necessary_pairs(self):
        logger.info('Downloading necessary package(s) for %s' % self.pair)
        if self.pair in self.pair_packages() or self.pair_inverse in self.pair_packages():
            self.download_pair()
        else:
            self.download_intermediary_pairs()

    def download_pair(self, pair = None):
        if pair is None: pair = self.pair
        # All commands must be run from the pack dir
        return self.repository.install_pair_package(pair)

    def download_intermediary_pairs(self):
        for pair in self.intermediary_pairs:
            self.download_pair(pair)

    def lang_tree(self, lang, pairs, depth = 2):
        tree = dict(lang = lang, children = dict())
        for pair in pairs:
            if lang in pair and depth > 0:
                child_lang = next(l for l in pair if l != lang)
                tree["children"][child_lang] = self.lang_tree(child_lang, pairs, depth - 1)
        return tree

    def first_pairs_path(self, leaf, lang):
        path = []
        for child_leaf in leaf['children'].values():
            if self.leaf_has_lang(child_leaf, lang):
                path.append(child_leaf['lang'])
                path = path + self.first_pairs_path(child_leaf, lang)
                break
        return path

    def leaf_has_lang(self, leaf, lang):
        children = leaf['children'].values()
        return lang in leaf['children'] or any(self.leaf_has_lang(child_leaf, lang) for child_leaf in children)

    def translate(self, input):
        for pair in self.pairs_pipeline:
            # Create a sub-process witch can receive a input
            input = self.translate_with_apertium(input, pair)
        return input

    def translate_with_apertium(self, input, pair):
        try:
            # Works with a temporary file as buffer (opened in text mode)
            with NamedTemporaryFile(mode='w+t') as temp_input_file:
                temp_input_file.writelines(input)
                temp_input_file.seek(0)
                input_translated = apertium('-ud', self.pack_dir, pair, temp_input_file.name)
        except ErrorReturnCode as e:
            raise Exception('Unable to translate this string.')
        return str(input_translated)
