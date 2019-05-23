import click

from es_translator import EsTranslator
from es_translator.logger import add_sysload_handler
from tempfile import mkdtemp

@click.command()
@click.option('--url', help='Elastichsearch URL', required=True)
@click.option('--index', help='Elastichsearch Index', required=True)
@click.option('--source-language', help='Source language to translate from', required=True)
@click.option('--target-language', help='Target language to translate to', required=True)
@click.option('--intermediary-language', help='An intermediary language to use when no translation is available between the source and the target. If none is provided this will be calculated automaticly.')
@click.option('--source-field', help='Document field to translate', default="content")
@click.option('--target-field', help='Document field to translate', default="content_translated")
@click.option('--query-string', help='Search query string to filter result')
@click.option('--data-dir', help='Path to the directory where to language model will be downloaded', type=click.Path(exists=True, dir_okay=True, writable=True, readable=True), default=mkdtemp())
@click.option('--scan-scroll', help='Scroll duration (set to higher value if you\'re processing a lot of documents)', default="5m")
@click.option('--dry-run', help='Don\'t save anything in Elasticsearch', is_flag=True, default=False)
@click.option('--pool-size', help='Number of parallel processes to start', default=1)
@click.option('--pool-timeout', help='Timeout to add a translation', default=60 * 30)
@click.option('--syslog-address', help='Syslog address', default='localhost')
@click.option('--syslog-port', help='Syslog port', default=514)
@click.option('--syslog-facility', help='Syslog facility', default='local7')
def main(syslog_address, syslog_port, syslog_facility, **options):
    add_sysload_handler(syslog_address, syslog_port, syslog_facility)
    EsTranslator(options).start()
