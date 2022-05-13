import sys
from coloredlogs import StandardErrorHandler
from contextlib import contextmanager
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from multiprocessing import Pool, JoinableQueue
from queue import Full
from os import path
from rich.progress import Progress
from time import sleep
# Module from the same package
from es_translator.es import TranslatedHit
from es_translator.logger import logger


def translation_worker(queue):
    while True:
        try:
            es_translator, hit, index, throttle = queue.get(True)
            logger.info('Translating doc %s (%s)' % (index, hit.meta.id))
            translated_hit = TranslatedHit(hit, es_translator.source_field, es_translator.target_field)
            translated_hit.add_translation(es_translator.interpreter)
            logger.info('Translated doc %s (%s)' % (index, hit.meta.id))
            # Skip on dry run
            if not es_translator.dry_run:
                # Create a new  client to
                client = Elasticsearch(es_translator.url)
                translated_hit.save(client)
                logger.info('Saved translation for doc %s (%s)' % (index, hit.meta.id))
            queue.task_done()
            sleep(throttle / 1000)
        except Exception as error:
            logger.warning('Unable to translate doc %s (%s)' % (index, hit.meta.id))
            logger.warning(error)
            queue.task_done()


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
        with self.print_done('Instantiating %s interpreter' % self.Interpreter.name):
            self.interpreter = self.init_interpreter()

        total = self.search().count()
        desc = 'Translating %s document(s)' % total

        with self.print_done(desc):
            # Add missing field and change the scroll duration
            search = self.search()
            search = search.source([self.source_field, self.target_field, '_routing'])
            search = search.params(scroll=self.scan_scroll)
            # Create a queue that is able to translate documents in parallel
            translation_queue = JoinableQueue(self.pool_size)
            # We create a pool
            with Pool(self.pool_size, translation_worker, (translation_queue,)):
                with Progress(disable=self.no_progressbar, transient=True) as progress:   
                    documents = search.scan()         
                    task = progress.add_task(desc, total=total)
                    for index, hit in enumerate(documents):
                        translation_queue.put((self, hit, index, self.throttle), True, self.pool_timeout)
                        progress.advance(task)
                    translation_queue.join()
                    

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
    def print_done(self, str, quiet = False):
        logger.info(str)
        # Avoid conflicting with a high log level
        if self.stdout_loglevel > 20:
            str = '\r%s...' % str
            self.print_flush(str)
            try:
                yield
                print('{0} \033[92mdone\033[0m'.format(str))
            except Full:
                logger.error('Timeout reached (%ss).' % self.pool_timeout)
                print('{0} \033[91merror\033[0m'.format(str))
            except Exception as error:
                logger.error(error, exc_info=True)
                print('{0} \033[91merror\033[0m'.format(str))
                if not quiet: raise error
                sys.exit(1)
        else:
            yield
