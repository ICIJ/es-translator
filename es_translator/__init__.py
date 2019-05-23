
import sys
import itertools
from contextlib import contextmanager
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from es_translator.apertium import Apertium
from es_translator.es import TranslatedHit
from es_translator.logger import logger
from multiprocessing import Pool

def translation_worker(es_translator, hit, index):
    try:
        logger.info('Translating doc %s (%s)' % (index, hit.meta.id))
        translated_hit = TranslatedHit(hit, es_translator.source_field, es_translator.target_field)
        translated_hit.add_translation(es_translator.apertium)
        logger.info('Translated doc %s (%s)' % (index, hit.meta.id))
        # Skip on dry run
        if not es_translator.dry_run:
            # Create a new  client to
            client = Elasticsearch(es_translator.url)
            translated_hit.save(client)
            logger.info('Saved translation for doc %s (%s)' % (index, hit.meta.id))
    except Exception as e:
        logger.warning('Unable to translate doc %s (%s)' % (index, hit.meta.id))

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

    def start(self):
        with self.print_done('Instantiating Apertium'):
            self.apertium = self.init_apertium()

        with self.print_done('Translating %s document(s)' % self.search().execute().hits.total):
            # Add missing field and change the scroll duration
            search = self.search()
            search = search.source([self.source_field, self.target_field, '_routing'])
            search = search.params(scroll=self.scan_scroll)
            # We create a pool
            with Pool(self.pool_size) as pool:
                # Use scrolling mecanism from Elasticsearch to iterate over each result
                # and we group search result in bucket of the size of the pool
                for group_index, hit_group in enumerate(self.grouper(search.scan(), self.pool_size)):
                    group_offset = group_index * self.pool_size
                    hit_group = [[self, hit, group_offset + hit_index] for hit_index, hit in enumerate(hit_group)]
                    pool.starmap(translation_worker, hit_group)
        logger.info('Done!')

    def search(self):
        es_client = Elasticsearch(self.url)
        search = Search(index=self.index, using=es_client)
        # Add query_string to the search
        if self.query_string: search = search.query("query_string", query=self.query_string)
        return search

    def init_apertium(self):
        return Apertium(self.source_language, self.target_language, self.intermediary_language, self.data_dir)

    def print_flush(self, str):
        sys.stdout.write('\r{0}'.format(str))
        sys.stdout.flush()

    def grouper(self, iterable, n):
        iterable = iter(iterable)
        while True:
            tup = tuple(itertools.islice(iterable, 0, n))
            if tup:
                yield tup
            else:
                break

    @contextmanager
    def print_done(self, str, quiet = False):
        logger.info(str)
        str = '\r%s...' % str
        self.print_flush(str)
        try:
            yield
            print('{0} \033[92mdone\033[0m'.format(str))
        except Exception as error:
            logger.error(error, exc_info=True)
            print('{0} \033[91merror\033[0m'.format(str))
            if not quiet: raise error
            sys.exit(1)
