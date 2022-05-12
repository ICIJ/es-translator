from tempfile import NamedTemporaryFile
from functools import lru_cache
from sh import apertium, ErrorReturnCode
# Module from the same package
from .repository import ApertiumRepository
from ..abstract import AbstractInterpreter
from ...alpha import to_alpha_3_pair
from ...logger import logger

class Apertium(AbstractInterpreter):
    name = 'APERTIUM'
    
    def __init__(self, source = None, target = None, intermediary = None, pack_dir = None):
        super().__init__(source, target, intermediary, pack_dir)
        # A class to download necessary pair package
        self.repository = ApertiumRepository(self.pack_dir)
        # Raise an exception if the language pair is unkown
        if not self.is_pair_available and self.has_pair:
            try:
                self.download_necessary_pairs()
            except StopIteration:
                raise Exception('The pair is not available')
        else:
            logger.info('Existing package(s) found for pair %s' % self.pair)

    @property
    def pair_package(self):
        return self.pair_to_pair_package(self.pair)

    @property
    def is_pair_available(self):
        return not self.intermediary and self.pair in self.local_pairs

    @property
    def pairs_pipeline(self):
        if self.intermediary:
            return [self.intermediary_source_pair, self.intermediary_target_pair]
        else:
            return [self.pair_alpha_3]

    @property
    def intermediary_source_pair(self):
        return '%s-%s' % (self.source_alpha_3, self.intermediary_alpha_3)

    @property
    def intermediary_source_pair_package(self):
        return self.pair_to_pair_package(self.intermediary_source_pair)

    @property
    def intermediary_target_pair(self):
        return '%s-%s' % (self.intermediary_alpha_3, self.target_alpha_3)

    @property
    def intermediary_target_pair_package(self):
        return self.pair_to_pair_package(self.intermediary_target_pair)

    @property
    def intermediary_pairs(self):
        # Find the intermediary lang only if not given
        if self.intermediary is None:
            trunk_packages = [ s.split('-') for s in self.remote_pairs ]
            # Build a tree of languages and their children
            packages_tree = self.lang_tree(self.source, trunk_packages)
            # Find the first path between self.source (the root) and self.target in the given tree
            self.intermediary = self.first_pairs_path(packages_tree, self.target)[0]
        # We build the two intermediary pairs
        return [ self.intermediary_source_pair, self.intermediary_target_pair ]

    @property
    def local_pairs(self):
        output = apertium('-d', self.pack_dir, '-l').strip()
        return [ s.strip() for s in output.split('\n') ]

    @property
    @lru_cache()
    def remote_pairs(self, module = 'trunk'):
        packages = self.repository.pair_packages
        pairs = []
        package_name_to_pair = lambda n: '-'.join(n.split('-')[-2:])
        # Extract package within these two properties
        for attr in ['Package', 'Provides']:
            for package in packages:
                for value in package.get(attr, '').split(','):
                    pair = package_name_to_pair(value.strip())
                    pairs.append(pair)
        # Remove empty values
        return [ p for p in pairs if p != '']

    def pair_to_pair_package(self, pair):
        pair_inversed = '-'.join(pair.split('-')[::-1])
        combinations = [to_alpha_3_pair(pair), to_alpha_3_pair(pair_inversed)]
        try:
            return next(p for p in self.remote_pairs if p in combinations)
        except StopIteration:
            return None

    def download_necessary_pairs(self):
        logger.info('Downloading necessary package(s) for %s' % self.pair)
        if self.any_pair_variant_in_packages:
            self.download_pair()
        else:
            self.download_intermediary_pairs()

    def download_pair(self, pair = None):
        if pair is None:
            pair = self.pair_alpha_3
        else:
            pair = to_alpha_3_pair(pair)
        # All commands must be run from the pack dir
        return self.repository.install_pair_package(pair)

    @property
    def any_pair_variant_in_packages(self):
        return self.pair_alpha_3 in self.remote_pairs

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
