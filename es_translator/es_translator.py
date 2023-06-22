import sys
from coloredlogs import StandardErrorHandler
from contextlib import contextmanager
from elasticsearch import Elasticsearch, ElasticsearchException
from elasticsearch_dsl import Document, Search
from multiprocessing import Pool, JoinableQueue, Manager
from queue import Full
from os import path
from rich.progress import Progress
from typing import Any, ContextManager, Dict, List

# Module from the same package
from es_translator.interpreters import Apertium, Argos
from es_translator.logger import logger
from es_translator.worker import translation_worker, FatalTranslationException
from es_translator.tasks import translate_document_task
from es_translator.es import TranslatedHit


class EsTranslator:
    def __init__(self, options: Dict[str, Any]):
        """Initialize the Elasticsearch translator.

        Args:
            options (Dict[str, Any]): A dictionary of options needed to set up the translator.
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
        self.pool_size = options['pool_size']
        self.pool_timeout = options['pool_timeout']
        self.throttle = options['throttle']
        self.progressbar = options.get('progressbar', False)
        self.interpreter_name = options['interpreter']
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
        """Starts the translation process."""
        self.instantiate_interpreter()
        total = self.search().count()
        desc = 'Translating %s document(s)' % total
        with self.print_done(desc):
            search = self.configure_search()
            translation_queue = self.create_translation_queue()
            with self.with_shared_fatal_error() as shared_fatal_error:
                self.translate_documents_in_pool(
                    search, translation_queue, shared_fatal_error, total)

    def start_later(self):
        """Plan the translation process."""
        self.instantiate_interpreter()
        total = self.search().count()
        desc = f"Planning translation for {total} document{'s'[:total^1]}"
        with self.print_done(desc):
            search = self.configure_search()
            for hit in search.scan():
                logger.info(f'Planned translation for doc {hit.meta.id}')
                translate_document_task.delay(self.options, hit.meta.to_dict())

    @property
    def options(self):
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
            'pool_size': self.pool_size,
            'pool_timeout': self.pool_timeout,
            'throttle': self.throttle,
            'progressbar': self.progressbar,
            'interpreter': self.interpreter_name
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
    def search_source(self) -> List[str]:
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
    def with_shared_fatal_error(self) -> ContextManager:
        """Creates a context manager for managing shared fatal errors.

        Returns:
            ContextManager: A context manager.
        """
        with Manager() as manager:
            yield manager.Value('b', None)

    def find_document(self, params: Dict[str, str]):
        using = Elasticsearch(self.url)
        routing = getattr(params, 'routing', params['id'])
        return Document.get(
            index=params['index'],
            id=params['id'],
            routing=routing,
            using=using)

    def translate_document(self, hit):
        self.instantiate_interpreter()
        # Translate the document
        logger.info(f'Translating doc {hit.meta.id}')
        translated_hit = TranslatedHit(
            hit, self.source_field, self.target_field)
        translated_hit.add_translation(self.interpreter)
        logger.info(f'Translated doc {hit.meta.id}')
        # Save the translated document if not in dry run mode
        if not self.dry_run:
            client = Elasticsearch(self.url)
            translated_hit.save(client)
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
        with Pool(self.pool_size, translation_worker, (translation_queue, shared_fatal_error)):
            with Progress(disable=self.no_progressbar, transient=True) as progress:
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
        using = Elasticsearch(self.url)
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
        """Prints and flushes a string to stdout.

        Args:
            string (str): The string to be printed.
        """
        sys.stdout.write('\r{0}'.format(string))
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
    def print_done(self, string: str) -> ContextManager:
        """Prints a string and yields.

        Args:
            string (str): The string to be printed.

        Returns:
            ContextManager: A context manager.
        """
        logger.info(string)
        if self.stdout_loglevel > 20:
            string = '\r%s...' % string
            self.print_flush(string)
            try:
                yield
                print('{0} \033[92mdone\033[0m'.format(string))
            except (FatalTranslationException, ElasticsearchException, Full) as error:
                logger.error(error, exc_info=True)
                print('{0} \033[91merror\033[0m'.format(string))
                sys.exit(1)
        else:
            yield
