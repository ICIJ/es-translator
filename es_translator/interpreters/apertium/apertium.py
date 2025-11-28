"""Apertium interpreter for translation operations.

This module provides the Apertium interpreter class that interfaces with the
Apertium translation engine to perform language translations, including support
for intermediary language pairs when direct translation is unavailable.
"""
from functools import lru_cache
from tempfile import NamedTemporaryFile
from typing import Optional

from sh import ErrorReturnCode, apertium

from ...alpha import to_alpha_3_pair
from ...logger import logger
from ..abstract import AbstractInterpreter

# Module from the same package
from .repository import ApertiumRepository


class Apertium(AbstractInterpreter):
    """Apertium translation interpreter.

    Provides translation capabilities using the Apertium translation engine,
    with support for direct translation and intermediary language pairs.

    Attributes:
        name: Identifier for this interpreter ('APERTIUM').
        repository: ApertiumRepository instance for package management.
    """
    name = 'APERTIUM'

    def __init__(
            self,
            source: Optional[str] = None,
            target: Optional[str] = None,
            intermediary: Optional[str] = None,
            pack_dir: Optional[str] = None) -> None:
        """Initialize the Apertium interpreter.

        Args:
            source: Source language code.
            target: Target language code.
            intermediary: Optional intermediary language for indirect translation.
            pack_dir: Directory for storing translation packages.

        Raises:
            Exception: If the language pair is not available in the repository.
        """
        super().__init__(source, target, intermediary, pack_dir)
        # A class to download necessary pair package
        self.repository = ApertiumRepository(self.pack_dir)
        # Raise an exception if the language pair is unknown
        if not self.is_pair_available and self.has_pair:
            try:
                self.download_necessary_pairs()
            except StopIteration:
                raise Exception('The pair is not available')
        else:
            logger.info(f'Existing package(s) found for pair {self.pair}')

    @property
    def pair_package(self) -> Optional[str]:
        """Get the package name for the current language pair.

        Returns:
            Package name string or None if not found.
        """
        return self.pair_to_pair_package(self.pair)

    @property
    def is_pair_available(self) -> bool:
        """Check if the language pair is available locally.

        Returns:
            True if pair is available without intermediary.
        """
        return not self.intermediary and self.pair in self.local_pairs

    @property
    def pairs_pipeline(self) -> list[str]:
        """Get the translation pipeline (direct or via intermediary).

        Returns:
            List of language pair codes to process sequentially.
        """
        if self.intermediary:
            return [
                self.intermediary_source_pair,
                self.intermediary_target_pair]
        else:
            return [self.pair_alpha_3]

    @property
    def intermediary_source_pair(self) -> str:
        """Get source-to-intermediary language pair.

        Returns:
            Language pair string (e.g., 'eng-spa').
        """
        return f'{self.source_alpha_3}-{self.intermediary_alpha_3}'

    @property
    def intermediary_source_pair_package(self) -> Optional[str]:
        """Get package name for source-to-intermediary pair.

        Returns:
            Package name string or None if not found.
        """
        return self.pair_to_pair_package(self.intermediary_source_pair)

    @property
    def intermediary_target_pair(self) -> str:
        """Get intermediary-to-target language pair.

        Returns:
            Language pair string (e.g., 'spa-fra').
        """
        return f'{self.intermediary_alpha_3}-{self.target_alpha_3}'

    @property
    def intermediary_target_pair_package(self) -> Optional[str]:
        """Get package name for intermediary-to-target pair.

        Returns:
            Package name string or None if not found.
        """
        return self.pair_to_pair_package(self.intermediary_target_pair)

    @property
    def intermediary_pairs(self) -> list[str]:
        """Get intermediary language pairs for indirect translation.

        Automatically finds an intermediary language if not specified
        by building a language tree and finding a path from source to target.

        Returns:
            List of two language pair strings for indirect translation.
        """
        # Find the intermediary lang only if not given
        if self.intermediary is None:
            trunk_packages = [s.split('-') for s in self.remote_pairs]
            # Build a tree of languages and their children
            packages_tree = self.lang_tree(self.source, trunk_packages)
            # Find the first path between self.source (the root) and
            # self.target in the given tree
            self.intermediary = self.first_pairs_path(
                packages_tree, self.target)[0]
        # We build the two intermediary pairs
        return [self.intermediary_source_pair, self.intermediary_target_pair]

    @property
    def local_pairs(self) -> list[str]:
        """Get locally installed language pairs.

        Returns:
            List of locally available language pair codes.
        """
        output = apertium('-d', self.pack_dir, '-l').strip()
        return [s.strip() for s in output.split('\n')]

    @property
    @lru_cache
    def remote_pairs(self, module: str = 'trunk') -> list[str]:
        """Get remotely available language pairs from repository.

        Args:
            module: Repository module to query (default: 'trunk').

        Returns:
            List of available language pair codes from the repository.
        """
        packages = self.repository.pair_packages
        pairs = []
        def package_name_to_pair(n: str) -> str:
            return '-'.join(n.split('-')[-2:])
        # Extract package within these two properties
        for attr in ['Package', 'Provides']:
            for package in packages:
                for value in package.get(attr, '').split(','):
                    pair = package_name_to_pair(value.strip())
                    pairs.append(pair)
        # Remove empty values
        return [p for p in pairs if p != '']

    def pair_to_pair_package(self, pair: str) -> Optional[str]:
        """Convert language pair to package name.

        Checks both the pair and its reverse for availability in remote packages.

        Args:
            pair: Language pair string (e.g., 'en-es').

        Returns:
            Package name if found, None otherwise.
        """
        pair_inversed = '-'.join(pair.split('-')[::-1])
        combinations = [to_alpha_3_pair(pair), to_alpha_3_pair(pair_inversed)]
        try:
            return next(p for p in self.remote_pairs if p in combinations)
        except StopIteration:
            return None

    def download_necessary_pairs(self) -> None:
        """Download required language pair packages.

        Downloads either a direct pair or intermediary pairs depending on
        availability in the repository.
        """
        logger.info(f'Downloading necessary package(s) for {self.pair}')
        if self.any_pair_variant_in_packages:
            self.download_pair()
        else:
            self.download_intermediary_pairs()

    def download_pair(self, pair: Optional[str] = None) -> str:
        """Download and install a specific language pair package.

        Args:
            pair: Language pair to download. If None, uses current pair.

        Returns:
            Path to the installed package directory.
        """
        pair = self.pair_alpha_3 if pair is None else to_alpha_3_pair(pair)
        # All commands must be run from the pack dir
        return self.repository.install_pair_package(pair)

    @property
    def any_pair_variant_in_packages(self) -> bool:
        """Check if any variant of the current pair exists in packages.

        Returns:
            True if the pair is available in remote repository.
        """
        return self.pair_alpha_3 in self.remote_pairs

    def download_intermediary_pairs(self) -> None:
        """Download both intermediary language pairs for indirect translation."""
        for pair in self.intermediary_pairs:
            self.download_pair(pair)

    def lang_tree(self, lang: str, pairs: list[list[str]], depth: int = 2) -> dict:
        """Build a tree of language connections from available pairs.

        Args:
            lang: Root language for the tree.
            pairs: List of language pair lists.
            depth: Maximum depth to traverse (default: 2).

        Returns:
            Dictionary tree structure with 'lang' and 'children' keys.
        """
        tree = {'lang': lang, 'children': {}}
        for pair in pairs:
            if lang in pair and depth > 0:
                child_lang = next(item for item in pair if item != lang)
                tree["children"][child_lang] = self.lang_tree(
                    child_lang, pairs, depth - 1)
        return tree

    def first_pairs_path(self, leaf: dict, lang: str) -> list[str]:
        """Find the first path from a tree leaf to a target language.

        Args:
            leaf: Tree node dictionary with 'lang' and 'children' keys.
            lang: Target language to find path to.

        Returns:
            List of language codes forming the path.
        """
        path = []
        for child_leaf in leaf['children'].values():
            if self.leaf_has_lang(child_leaf, lang):
                path.append(child_leaf['lang'])
                path = path + self.first_pairs_path(child_leaf, lang)
                break
        return path

    def leaf_has_lang(self, leaf: dict, lang: str) -> bool:
        """Check if a tree leaf contains or leads to a target language.

        Args:
            leaf: Tree node dictionary with 'lang' and 'children' keys.
            lang: Target language to search for.

        Returns:
            True if the language is found in the leaf or its descendants.
        """
        children = leaf['children'].values()
        return lang in leaf['children'] or any(
            self.leaf_has_lang(
                child_leaf,
                lang) for child_leaf in children)

    def translate(self, input: str) -> str:
        """Translate text through the translation pipeline.

        If using an intermediary language, translates through multiple pairs.

        Args:
            input: Text to translate.

        Returns:
            Translated text string.
        """
        for pair in self.pairs_pipeline:
            # Create a sub-process which can receive an input
            input = self.translate_with_apertium(input, pair)
        return input

    def translate_with_apertium(self, input: str, pair: str) -> str:
        """Translate text using Apertium for a specific language pair.

        Args:
            input: Text to translate.
            pair: Language pair code (e.g., 'eng-spa').

        Returns:
            Translated text string.

        Raises:
            Exception: If translation fails.
        """
        try:
            # Works with a temporary file as buffer (opened in text mode)
            with NamedTemporaryFile(mode='w+t') as temp_input_file:
                temp_input_file.writelines(input)
                temp_input_file.seek(0)
                input_translated = apertium(
                    '-ud', self.pack_dir, pair, temp_input_file.name)
        except ErrorReturnCode:
            raise Exception('Unable to translate this string.')
        return str(input_translated)
