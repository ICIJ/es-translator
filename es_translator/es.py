from typing import Any, Optional

from elasticsearch import Elasticsearch
from elasticsearch_dsl.utils import ObjectBase

from es_translator.interpreters.abstract import AbstractInterpreter


class TranslatedHit:
    """Wrapper for Elasticsearch document hits with translation support.

    This class wraps an Elasticsearch document hit and provides methods
    for adding translations and saving the updated document back to
    Elasticsearch.

    Attributes:
        hit: The original Elasticsearch document hit.
        source_field: Field name containing the source text.
        target_field: Field name for storing translations.
        force: If True, re-translate even if translation exists.
    """

    def __init__(
        self,
        hit: ObjectBase,
        source_field: str = 'content',
        target_field: str = 'content_translated',
        force: bool = False,
    ) -> None:
        """Initialize the TranslatedHit wrapper.

        Args:
            hit: Elasticsearch document hit object.
            source_field: Field name containing the source text.
            target_field: Field name for storing translations.
            force: If True, re-translate even if translation exists.
        """
        self.hit = hit
        self.source_field = source_field
        self.target_field = target_field
        # Ensure the target field is an array
        self.hit[self.target_field] = self.translations
        # Force translation even if it already exists
        self.force = force

    @property
    def source_value(self) -> Optional[str]:
        """Get the source text value from the document.

        Returns:
            The source text content, or None if not present.
        """
        return self.hit.to_dict().get(self.source_field)

    @property
    def translations(self) -> list[dict[str, str]]:
        """Get existing translations from the document.

        Returns:
            List of translation dictionaries.
        """
        return self.hit.to_dict().get(self.target_field, [])

    @property
    def id(self) -> str:
        """Get the document ID.

        Returns:
            The Elasticsearch document ID.
        """
        return self.hit.meta.id

    @property
    def routing(self) -> Optional[str]:
        """Get the document routing value.

        Returns:
            The routing value, or None if not set.
        """
        return self.hit.meta.to_dict().get('routing', None)

    @property
    def index(self) -> str:
        """Get the index name.

        Returns:
            The Elasticsearch index name.
        """
        return self.hit.meta.index

    @property
    def body(self) -> dict[str, Any]:
        """Build the update body for Elasticsearch.

        Returns:
            Dictionary with the document update structure.
        """
        return {'doc': {self.target_field: self.translations}}

    def save(self, client: Elasticsearch) -> None:
        """Save the translated document to Elasticsearch.

        Args:
            client: Elasticsearch client instance.
        """
        client.update(index=self.index, id=self.id, routing=self.routing, body=self.body)

    def add_translation(self, interpreter: AbstractInterpreter, max_content_length: int = -1) -> None:
        """Add a translation to the document.

        Translates the source content using the provided interpreter and
        appends the result to the translations list.

        Args:
            interpreter: Translation interpreter to use.
            max_content_length: Maximum length for translated content.
                Use -1 for unlimited.
        """
        if self.force or not self.is_translated(interpreter.source_name, interpreter.target_name, interpreter.name):
            content = interpreter.translate(self.source_value)
            truncated_content = content if max_content_length == -1 else content[:max_content_length]
            self.hit[self.target_field].append(
                {
                    'translator': interpreter.name,
                    'source_language': interpreter.source_name.upper(),
                    'target_language': interpreter.target_name.upper(),
                    'content': truncated_content,
                }
            )

    def is_translated(self, source_language: str, target_language: str, translator: str) -> bool:
        """Check if the document has already been translated.

        Args:
            source_language: Source language name.
            target_language: Target language name.
            translator: Translator/interpreter name.

        Returns:
            True if a matching translation exists, False otherwise.
        """

        def same_languages(t: dict[str, str]) -> bool:
            return (
                t['source_language'] == source_language.upper()
                and t['target_language'] == target_language.upper()
                and t['translator'] == translator
            )

        return any(t for t in self.translations if same_languages(t))
