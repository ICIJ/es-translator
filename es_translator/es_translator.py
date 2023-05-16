import sys
from coloredlogs import StandardErrorHandler
from contextlib import contextmanager
from elasticsearch import Elasticsearch, ElasticsearchException
from elasticsearch_dsl import Search
from multiprocessing import Pool, JoinableQueue, Manager
from queue import Full
from os import path
from rich.progress import Progress
# Module from the same package
from es_translator.logger import logger
from es_translator.worker import translation_worker, FatalTranslationException

class EsTranslator:
    def __init__(self, options):
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
        self.dry_run = options['dry_run']
        self.pool_size = options['pool_size']
        self.pool_timeout = options['pool_timeout']
        self.throttle = options['throttle']
        self.progressbar = options['progressbar']
        # The "interpreter" option is a class
        self.Interpreter = options['interpreter']

    @property
    def no_progressbar(self):
        return not self.progressbar
    
    def start(self):
        # Instantiate the interpreter
        self.instantiate_interpreter()
        # Count the total number of documents
        total = self.search().count()
        desc = 'Translating %s document(s)' % total
        # Start the translation process
        with self.print_done(desc):
            # Configure the search object
            search = self.configure_search()
            # Create a queue to translate documents in parallel
            translation_queue = self.create_translation_queue()
            # Create a shared variable to track fatal errors
            with self.with_shared_fatal_error() as shared_fatal_error: 
                # Translate the documents
                self.translate_documents(search, translation_queue, shared_fatal_error, total)

    def instantiate_interpreter(self):
        with self.print_done('Instantiating %s interpreter' % self.Interpreter.name):
            self.interpreter = self.init_interpreter()
        return self.interpreter

    def configure_search(self):
        # Configure the search object
        search = self.search()
        search = search.source([self.source_field, self.target_field, '_routing'])
        search = search.params(scroll=self.scan_scroll, size=self.pool_size)
        return search

    def create_translation_queue(self):
        # Create a queue that is able to translate documents in parallel
        return JoinableQueue(self.pool_size)

    @contextmanager
    def with_shared_fatal_error(self):
        # Use Manager to create a shared variable (shared_fatal_error)
        with Manager() as manager:
            # Shared variable between threads, initialized as None
            yield manager.Value('b', None)

    def translate_documents(self, search, translation_queue, shared_fatal_error, total):
        # Start a pool of worker processes
        with Pool(self.pool_size, translation_worker, (translation_queue, shared_fatal_error)):
            # Create a progress bar
            with Progress(disable=self.no_progressbar, transient=True) as progress:
                documents = search.scan()
                task = progress.add_task('Translating %s document(s)' % total, total=total)
                for index, hit in enumerate(documents):
                    self.process_document(translation_queue, hit, index, progress, task, shared_fatal_error)
                translation_queue.join()

    def process_document(self, translation_queue, hit, index, progress, task, shared_fatal_error):
        # Add the document to the translation queue
        translation_queue.put((self, hit, index), True, self.pool_timeout)
        
        # Update the progress bar with the current task
        progress.advance(task)
        
        # Check if a fatal error occurred
        if shared_fatal_error.value:
            # Raise an exception to interrupt the loop
            raise FatalTranslationException(shared_fatal_error.value)
    
    def search(self):
        es_client = Elasticsearch(self.url)
        search = Search(index=self.index, using=es_client)
        # Add query_string to the search
        if self.query_string:
            search = search.query("query_string", query=self.query_string)
        return search

    def init_interpreter(self):
        pack_dir = path.join(self.data_dir, 'packs', self.Interpreter.name)
        return self.Interpreter(self.source_language, self.target_language, self.intermediary_language, pack_dir)

    def print_flush(self, str):
        sys.stdout.write('\r{0}'.format(str))
        sys.stdout.flush()

    @property
    def stdout_loglevel(self):
        try:
            handler = next(h for h in logger.handlers if isinstance(h, StandardErrorHandler))
            return getattr(handler, 'level', 0)
        except StopIteration:
            return 0

    @contextmanager
    def print_done(self, str):
        logger.info(str)
        # Avoid conflicting with a high log level
        if self.stdout_loglevel > 20:
            str = '\r%s...' % str
            self.print_flush(str)
            try:
                yield
                print('{0} \033[92mdone\033[0m'.format(str))
            except (FatalTranslationException, ElasticsearchException, Full) as error:
                logger.error(error, exc_info=True)
                print('{0} \033[91merror\033[0m'.format(str))
                sys.exit(1)
        else:
            yield
