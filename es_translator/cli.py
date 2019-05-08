import click
import sys

from contextlib import contextmanager
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from es_translator.apertium import Apertium
from es_translator.es import TranslatedHit

def print_flush(str):
    sys.stdout.write('\r{0}'.format(str))
    sys.stdout.flush()

@contextmanager
def print_done(str):
    str = '\r%s' % str
    print_flush(str)
    yield
    print('{0} \033[92mdone\033[0m'.format(str))

@click.command()
@click.option('--url', help='Elastichsearch URL', default='http://localhost:9200')
@click.option('--index', help='Elastichsearch Index', default='void')
@click.option('--source-language', help='Source language to translate from', default="fr")
@click.option('--target-language', help='Target language to translate to', default="en")
@click.option('--intermediary-language', help='An intermediary language to use when no translation is available between the source and the target. If none is provided this will be calculated automaticly.')
@click.option('--source-field', help='Document field to translate', default="content")
@click.option('--target-field', help='Document field to translate', default="content_translated")
@click.option('--query', help='Search query string to filter result')
@click.option('--data-dir', help='Path to the directory where to language model will be downloaded')
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
    # Use scrolling mecanism from Elasticsearch to iterate over each result
    hits = search.source([options['source_field'], options['target_field'], '_routing']).scan()
    with click.progressbar(hits, label = 'Translating %s document(s)...' % total_hits, length = total_hits, width = 0) as bar:
        for hit in bar:
            # Extract the value from a dict to avoid failing when the field is missing
            translated_hit = TranslatedHit(hit, options['source_field'], options['target_field'])
            translated_hit.add_translation(apertium)
            translated_hit.save(client)
