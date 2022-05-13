import click
import logging

from es_translator import EsTranslator
from tempfile import mkdtemp
# Module from the same package
from es_translator.interpreters import Apertium, Argos
from es_translator.interpreters.apertium.pairs import Pairs
from es_translator.logger import add_syslog_handler, add_stdout_handler


def validate_loglevel(ctx, param, value):
    try:
        if isinstance(value, str):
            return getattr(logging, value)
        return int(value)
    except (AttributeError, ValueError):
        raise click.BadParameter('must be a valid log level (CRITICAL, ERROR, WARNING, INFO, DEBUG or NOTSET)')


def validate_progressbar(ctx, param, value):
    # If no value given, we activate the progress bar only when the
    # stdout_loglevel value is higher than INFO (20)
    return value if value is not None else ctx.params['stdout_loglevel'] > 20


def validate_interpreter(ctx, param, value):
    interpreters = ( Apertium, Argos, )
    for interpreter in interpreters:
        if value.upper() == interpreter.name.upper():
            return interpreter
    names = (interpreter.name for interpreter in interpreters)
    raise click.BadParameter('must be a valid interpreter name (%s)' % ', '.join(names))


@click.command()
@click.option('--url', help='Elastichsearch URL', required=True)
@click.option('--index', help='Elastichsearch Index', required=True)
@click.option('--interpreter', help='Interpreter to use to perform the translation', default='APERTIUM', callback=validate_interpreter)
@click.option('--source-language', help='Source language to translate from', required=True, default=None)
@click.option('--target-language', help='Target language to translate to', required=True, default=None)
@click.option('--intermediary-language', help='An intermediary language to use when no translation is available between the source and the target. If none is provided this will be calculated automatically.')
@click.option('--source-field', help='Document field to translate', default="content")
@click.option('--target-field', help='Document field where the translations are stored', default="content_translated")
@click.option('--query-string', help='Search query string to filter result')
@click.option('--data-dir', help='Path to the directory where to language model will be downloaded', type=click.Path(exists=True, dir_okay=True, writable=True, readable=True), default=mkdtemp())
@click.option('--scan-scroll', help='Scroll duration (set to higher value if you\'re processing a lot of documents)', default="5m")
@click.option('--dry-run', help='Don\'t save anything in Elasticsearch', is_flag=True, default=False)
@click.option('--pool-size', help='Number of parallel processes to start', default=1)
@click.option('--pool-timeout', help='Timeout to add a translation', default=60 * 30)
@click.option('--throttle', help='Throttle between each translation (in ms)', default=0)
@click.option('--syslog-address', help='Syslog address', default='localhost')
@click.option('--syslog-port', help='Syslog port', default=514)
@click.option('--syslog-facility', help='Syslog facility', default='local7')
@click.option('--stdout-loglevel', help='Change the default log level for stdout error handler', default='ERROR',
              callback=validate_loglevel)
@click.option('--progressbar/--no-progressbar', help='Display a progressbar', default=None,
            callback=validate_progressbar)
def translate(syslog_address, syslog_port, syslog_facility, **options):
    # Configure Syslog handler
    add_syslog_handler(syslog_address, syslog_port, syslog_facility)
    add_stdout_handler(options['stdout_loglevel'])
    # We pass all options to EsTranslator then we start the translation
    # from Elasticsearch. This will download required pairs if needed.
    EsTranslator(options).start()


@click.command()
@click.option('--data-dir', help='Path to the directory where to language model will be downloaded', type=click.Path(exists=True, dir_okay=True, writable=True, readable=True), default=mkdtemp())
@click.option('--local', help='List pairs available locally', is_flag=True, default=False)
@click.option('--syslog-address', help='Syslog address', default='localhost')
@click.option('--syslog-port', help='Syslog port', default=514)
@click.option('--syslog-facility', help='Syslog facility', default='local7')
@click.option('--stdout-loglevel', help='Change the default log level for stdout error handler', default='ERROR',
              callback=validate_loglevel)
def pairs(data_dir, local, syslog_address, syslog_port, syslog_facility, **options):
    # Configure Syslog handler
    add_syslog_handler(syslog_address, syslog_port, syslog_facility)
    add_stdout_handler(options['stdout_loglevel'])
    # Only the data-dir is needed to construct the Apertium instance, then
    # we just need to print the pair
    Pairs(data_dir, local).print_pairs()

if __name__ == '__main__':
    translate()
