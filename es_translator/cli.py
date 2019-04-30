import click
import sys

from contextlib import contextmanager
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from es_translator.apertium import Apertium

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
@click.option('--source-field', help='Document field to translate', default="content")
@click.option('--target-field', help='Document field to translate', default="content_translated")
@click.option('--query', help='Search query string to filter result')
@click.option('--data-dir', help='Path to the directory where to language model will be downloaded')
def main(**options):

    with print_done('Instantiating Apertium...'):
        apertium = Apertium(options['source_language'], options['target_language'], options['data_dir'])

    # Build the search
    client = Elasticsearch(options['url'])
    search = Search(index=options['index'])
    search = search.using(client)
    # Add query_string to the search
    if options['query']: search = search.query("query_string", query=options['query'])

    with print_done('Translating %s document(s)...' % search.execute().hits.total):
        # Use scrolling mecanism from Elasticsearch to iterate over each result
        for hit in search.source([options['source_field']]).scan():
            # Extract the value from a dict to avoid failing when the field is missing
            value = hit.to_dict().get(options['source_field'])
            translated = apertium.translate(value)
