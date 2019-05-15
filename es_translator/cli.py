import click
import sys

import itertools
from contextlib import contextmanager
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from es_translator.apertium import Apertium
from es_translator.es import TranslatedHit
from multiprocessing import Pool

def print_flush(str):
    sys.stdout.write('\r{0}'.format(str))
    sys.stdout.flush()

@contextmanager
def print_done(str):
    str = '\r%s' % str
    print_flush(str)
    yield
    print('{0} \033[92mdone\033[0m'.format(str))

def translate_hit(hit, apertium, options):
    # Extract the value from a dict to avoid failing when the field is missing
    translated_hit = TranslatedHit(hit, options['source_field'], options['target_field'])
    translated_hit.add_translation(apertium)
    # Skip on dry run
    if not options['dry_run']: translated_hit.save(client)


def grouper(iterable, n):
    iterable = iter(iterable)
    while True:
        tup = tuple(itertools.islice(iterable, 0, n))
        if tup:
            yield tup
        else:
            break

@click.command()
@click.option('--url', required=True, help='Elastichsearch URL')
@click.option('--index', required=True, help='Elastichsearch Index')
@click.option('--source-language', required=True, help='Source language to translate from')
@click.option('--target-language', required=True, help='Target language to translate to')
@click.option('--intermediary-language', help='An intermediary language to use when no translation is available between the source and the target. If none is provided this will be calculated automaticly.')
@click.option('--source-field', help='Document field to translate', default="content")
@click.option('--target-field', help='Document field to translate', default="content_translated")
@click.option('--query', help='Search query string to filter result')
@click.option('--data-dir', help='Path to the directory where to language model will be downloaded')
@click.option('--scan-scroll', help='Scroll duration (set to higher value if you\'re processing a lot of documents)', default="5m")
@click.option('--dry-run', help='Don\'t save anything in Elasticsearch', is_flag=True)
@click.option('--pool-size', help='Number of paralell processes to start', default=1)
def main(**options):
    with print_done('Instantiating Apertium...'):
        apertium = Apertium(options['source_language'], options['target_language'], options['intermediary_language'], options['data_dir'])
    # Build the search
    client = Elasticsearch(options['url'])
    search = Search(index=options['index'], using=client)
    # Add query_string to the search
    if options['query']:
        search = search.query("query_string", query=options['query'])
    total_hits = search.execute().hits.total
    search = search.source([options['source_field'], options['target_field'], '_routing'])
    search = search.params(scroll=options['scan_scroll'])
    # Use scrolling mecanism from Elasticsearch to iterate over each result
    hits = search.scan()
    with click.progressbar(hits, label = 'Translating %s document(s)...' % total_hits, length = total_hits, width = 0) as bar:
        # We group search result in bucket of the size of the pool
        for hit_group in grouper(bar, options['pool_size']):
            # We create a pool
            with Pool(options['pool_size']) as p:
                hit_group = ([hit, apertium, options] for hit in hit_group)
                p.starmap(translate_hit, hit_group)
