"""Elasticsearch translator for automated document translation.

This module provides the main EsTranslator class that orchestrates the translation
of documents in Elasticsearch indices using various translation interpreters.
"""
import sys
from collections.abc import Generator
from contextlib import contextmanager
from multiprocessing import JoinableQueue, Manager, Pool
from os import path
from queue import Full
from typing import Any

from coloredlogs import StandardErrorHandler
from elasticsearch import Elasticsearch, ElasticsearchException
from elasticsearch_dsl import Document, Search
from elasticsearch_dsl.utils import ObjectBase
from rich.progress import Progress

from es_translator.es import TranslatedHit

# Module from the same package
from es_translator.interpreters import Apertium, Argos
from es_translator.logger import logger
from es_translator.tasks import translate_document_task
from es_translator.worker import FatalTranslationException, translation_worker


class EsTranslator:
    """Orchestrates translation of Elasticsearch documents.

    Manages the translation workflow including searching for documents,
    parallel translation using worker pools, and updating translated documents.

    Attributes:
        url: Elasticsearch URL.
        index: Index name to search and update.
        source_language: Source language code.
        target_language: Target language code.
        intermediary_language: Optional intermediary language for indirect translation.
        source_field: Field name containing source text.
        target_field: Field name to store translated text.
        query_string: Optional Elasticsearch query string.
        data_dir: Directory for storing interpreter data.
        scan_scroll: Scroll timeout for search.
        dry_run: If True, skip saving translated documents.
        force: Force re-translation of already translated documents.
        pool_size: Number of parallel worker processes.
        pool_timeout: Timeout for worker pool operations.
        throttle: Throttle for rate limiting.
        progressbar: Show progress bar during translation.
        interpreter_name: Name of translation interpreter to use.
        max_content_length: Maximum content length to translate (-1 for unlimited).
        plan: If True, queue translations for later execution.
        interpreter: Instantiated interpreter instance.
    """

    def __init__(self, options: dict[str, Any]) -> None:
        """Initialize the Elasticsearch translator.

        Args:
            options: Dictionary of configuration options.
        """
        self.url = options['url']
        self.index = options['index']
        self.source_language = options['source_language']
        self.target_language = options['target_language']
        self.intermediary_language = options['intermediary_language']
        self.source_field = options['source_field']
        self.target_field = options['target_field']
        self.query_string = options['query_string']
        self.data_dir = options['data_dir']
        self.scan_scroll = options['scan_scroll']
        self.dry_run = options.get('dry_run', False)
        self.force = options['force']
        self.pool_size = options['pool_size']
        self.pool_timeout = options['pool_timeout']
        self.throttle = options['throttle']
        self.progressbar = options.get('progressbar', False)
        self.interpreter_name = options['interpreter']
        self.max_content_length = options.get('max_content_length', -1)
        self.plan = options.get('plan', False)

    @property
    def no_progressbar(self) -> bool:
        """Check if the progressbar option is set to False.

        Returns:
            bool: True if the progressbar option is False, else False.
        """
        return not self.progressbar

    def start(self) -> None:
        """Starts or plans the translation process."""
        if self.plan:
            self.start_later()
        else:
            self.start_now()

    def start_now(self) -> None:
        """Start the translation process immediately."""
        self.instantiate_interpreter()
        total = self.search().count()
        desc = f'Translating {total} document(s)'
        with self.print_done(desc):
            search = self.configure_search()
            translation_queue = self.create_translation_queue()
            with self.with_shared_fatal_error() as shared_fatal_error:
                self.translate_documents_in_pool(
                    search, translation_queue, shared_fatal_error, total)

    def start_later(self) -> None:
        """Queue translation tasks for later execution via Celery."""
        self.instantiate_interpreter()
        total = self.search().count()
        desc = f"Planning translation for {total} document{'s'[:total^1]}"
        with self.print_done(desc):
            search = self.configure_search()
            for hit in search.scan():
                logger.info(f'Planned translation for doc {hit.meta.id}')
                translate_document_task.delay(self.options, hit.meta.to_dict())

    @property
    def options(self) -> dict[str, Any]:
        """Get configuration options as a dictionary.

        Returns:
            Dictionary containing all configuration options.
        """
        return {
            'url': self.url,
            'index': self.index,
            'source_language': self.source_language,
            'target_language': self.target_language,
            'intermediary_language': self.intermediary_language,
            'source_field': self.source_field,
            'target_field': self.target_field,
            'query_string': self.query_string,
            'data_dir': self.data_dir,
            'scan_scroll': self.scan_scroll,
            'dry_run': self.dry_run,
            'force': self.force,
            'pool_size': self.pool_size,
            'pool_timeout': self.pool_timeout,
            'throttle': self.throttle,
            'progressbar': self.progressbar,
            'interpreter': self.interpreter_name,
            'max_content_length': self.max_content_length
        }

    def instantiate_interpreter(self) -> Any:
        """Instantiates the interpreter.

        Returns:
            Any: An instance of the interpreter.
        """
        if not hasattr(self, 'interpreter'):
            with self.print_done(f'Instantiating {self.interpreter_name} interpreter'):
                self.interpreter = self.init_interpreter()
        return self.interpreter

    def configure_search(self) -> Search:
        """Configures the search object.

        Returns:
            Search: A configured search object.
        """
        search = self.search()
        search = search.source(self.search_source)
        search = search.params(scroll=self.scan_scroll, size=self.pool_size)
        return search

    @property
    def search_source(self) -> list[str]:
        """Gets the list of fields to use in the search.

        Returns:
            List[str]: list of fields to use in the search.
        """
        if self.plan:
            return ['_routing', '_id']
        return [self.source_field, self.target_field, '_routing', '_id']


    def create_translation_queue(self) -> JoinableQueue:
        """Creates a queue that can translate documents in parallel.

        Returns:
            JoinableQueue: A queue for parallel document translation.
        """
        return JoinableQueue(self.pool_size)

    @contextmanager
    def with_shared_fatal_error(self) -> Generator[Any, None, None]:
        """Creates a context manager for managing shared fatal errors.

        Returns:
            Generator yielding a shared manager value.
        """
        with Manager() as manager:
            yield manager.Value('b', None)

    def find_document(self, params: dict[str, str]) -> Document:
        """Find a document by ID and routing.

        Args:
            params: Dictionary containing 'index', 'id', and optionally 'routing'.

        Returns:
            The found Document object.
        """
        using = self.create_client()
        routing = getattr(params, 'routing', params['id'])
        return Document.get(
            index=params['index'],
            id=params['id'],
            routing=routing,
            using=using)

    def translate_document(self, hit: ObjectBase) -> None:
        """Translate a single document.

        Args:
            hit: Document hit object to translate.
        """
        self.instantiate_interpreter()
        # Translate the document
        logger.info(f'Translating doc {hit.meta.id}')
        translated_hit = self.create_translated_hit(hit)
        translated_hit.add_translation(self.interpreter, max_content_length=self.max_content_length)
        logger.info(f'Translated doc {hit.meta.id}')
        # Save the translated document if not in dry run mode
        if not self.dry_run:
            translated_hit.save(self.create_client())
            logger.info(f'Saved translation for doc {hit.meta.id}')

    def translate_documents_in_pool(
            self,
            search: Search,
            translation_queue: JoinableQueue,
            shared_fatal_error: Manager,
            total: int) -> None:
        """Translates documents.

        Args:
            search (Search): A search object.
            translation_queue (JoinableQueue): A queue for parallel document translation.
            shared_fatal_error (Manager): A shared manager for fatal errors.
            total (int): The total number of documents.
        """
        with (
            Pool(self.pool_size, translation_worker, (translation_queue, shared_fatal_error)),
            Progress(disable=self.no_progressbar, transient=True) as progress,
        ):
            task = progress.add_task(
                f"Translating {total} document{'s'[:total^1]}", total=total)
            for hit in search.scan():
                self.process_document(
                    translation_queue, hit, progress, task, shared_fatal_error)
            translation_queue.join()

    def process_document(
            self,
            translation_queue: JoinableQueue,
            hit: Any,
            progress: Progress,
            task: Any,
            shared_fatal_error: Manager) -> None:
        """Processes a document.

        Args:
            translation_queue (JoinableQueue): A queue for parallel document translation.
            hit (Any): The document to be translated.
            index (int): The index of the document.
            progress (Progress): A progress object.
            task (Any): The current task.
            shared_fatal_error (Manager): A shared manager for fatal errors.
        """
        translation_queue.put((self, hit), True, self.pool_timeout)
        progress.advance(task)
        if shared_fatal_error.value:
            raise FatalTranslationException(shared_fatal_error.value)

    def search(self) -> Search:
        """Executes a search query.

        Returns:
            Search: The search result.
        """
        using = self.create_client()
        search = Search(index=self.index, using=using)
        if self.query_string:
            search = search.query("query_string", query=self.query_string)
        return search

    def init_interpreter(self) -> Any:
        """Initializes the interpreter.

        Returns:
            Any: The initialized interpreter.
        """
        pack_dir = path.join(self.data_dir, 'packs', self.interpreter_name)
        interpreters = (Apertium, Argos,)
        Interpreter = next(
            i for i in interpreters if i.name.lower() == self.interpreter_name.lower())
        return Interpreter(
            self.source_language,
            self.target_language,
            self.intermediary_language,
            pack_dir)

    def print_flush(self, string: str) -> None:
        """Print and flush a string to stdout.

        Args:
            string: The string to be printed.
        """
        sys.stdout.write(f'\r{string}')
        sys.stdout.flush()

    @property
    def stdout_loglevel(self) -> int:
        """Gets the log level of stdout.

        Returns:
            int: The log level of stdout.
        """
        try:
            handler = next(
                h for h in logger.handlers if isinstance(
                    h, StandardErrorHandler))
            return getattr(handler, 'level', 0)
        except StopIteration:
            return 0

    @contextmanager
    def print_done(self, string: str) -> Generator[None, None, None]:
        """Print progress message and yield, showing done/error status.

        Args:
            string: The status message to be printed.

        Returns:
            Generator for wrapping operations with status output.
        """
        logger.info(string)
        if self.stdout_loglevel > 20:
            string = f'\r{string}...'
            self.print_flush(string)
            try:
                yield
                print(f'{string} \033[92mdone\033[0m')
            except (FatalTranslationException, ElasticsearchException, Full) as error:
                logger.error(error, exc_info=True)
                print(f'{string} \033[91merror\033[0m')
                sys.exit(1)
        else:
            yield

    def create_translated_hit(self, hit: ObjectBase) -> TranslatedHit:
        """Create a TranslatedHit wrapper for a document hit.

        Args:
            hit: Document hit object.

        Returns:
            TranslatedHit instance ready for translation.
        """
        return TranslatedHit(hit, self.source_field, self.target_field, self.force)

    def create_client(self) -> Elasticsearch:
        """Create an Elasticsearch client instance.

        Returns:
            Configured Elasticsearch client.
        """
        return Elasticsearch(self.url)
