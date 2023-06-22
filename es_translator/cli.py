import click
import logging

from es_translator import EsTranslator
from tempfile import mkdtemp
# Module from the same package
from es_translator.interpreters import Apertium, Argos
from es_translator.interpreters.apertium.pairs import Pairs
from es_translator.logger import add_syslog_handler, add_stdout_handler
from es_translator.tasks import app as celery_app


def validate_loglevel(ctx, param, value):
    try:
        if isinstance(value, str):
            return getattr(logging, value)
        return int(value)
    except (AttributeError, ValueError):
        raise click.BadParameter(
            'must be a valid log level (CRITICAL, ERROR, WARNING, INFO, DEBUG or NOTSET)')


def validate_progressbar(ctx, param, value):
    # If no value given, we activate the progress bar only when the
    # stdout_loglevel value is higher than INFO (20)
    return value if value is not None else ctx.params['stdout_loglevel'] > 20


def validate_interpreter(ctx, param, value):
    interpreters = (Apertium, Argos, )
    for interpreter in interpreters:
        if value.upper() == interpreter.name.upper():
            return interpreter.name
    names = (interpreter.name for interpreter in interpreters)
    raise click.BadParameter(
        'must be a valid interpreter name (%s)' %
        ', '.join(names))


@click.command()
@click.option('-u', '--url', help='Elastichsearch URL',
              default="http://localhost:9200")
@click.option('-i', '--index', help='Elastichsearch Index', required=True)
@click.option('-r',
              '--interpreter',
              help='Interpreter to use to perform the translation',
              default='ARGOS',
              callback=validate_interpreter)
@click.option('-s',
              '--source-language',
              help='Source language to translate from',
              required=True,
              default=None)
@click.option('-t',
              '--target-language',
              help='Target language to translate to',
              required=True,
              default=None)
@click.option('--intermediary-language',
              help='An intermediary language to use when no translation is available between the source and the target. If none is provided this will be calculated automatically.')
@click.option('--source-field',
              help='Document field to translate',
              default="content")
@click.option('--target-field',
              help='Document field where the translations are stored',
              default="content_translated")
@click.option('-q', '--query-string',
              help='Search query string to filter result')
@click.option('-d',
              '--data-dir',
              help='Path to the directory where to language model will be downloaded',
              type=click.Path(exists=True,
                              dir_okay=True,
                              writable=True,
                              readable=True),
              default=mkdtemp())
@click.option('--scan-scroll',
              help='Scroll duration (set to higher value if you\'re processing a lot of documents)',
              default="5m")
@click.option('--dry-run',
              help='Don\'t save anything in Elasticsearch',
              is_flag=True,
              default=False)
@click.option('--pool-size',
              help='Number of parallel processes to start',
              default=1)
@click.option('--pool-timeout',
              help='Timeout to add a translation',
              default=60 * 30)
@click.option('--throttle',
              help='Throttle between each translation (in ms)',
              default=0)
@click.option('--syslog-address', help='Syslog address', default='localhost')
@click.option('--syslog-port', help='Syslog port', default=514)
@click.option('--syslog-facility', help='Syslog facility', default='local7')
@click.option('--stdout-loglevel',
              help='Change the default log level for stdout error handler',
              default='ERROR',
              callback=validate_loglevel)
@click.option('--progressbar/--no-progressbar',
              help='Display a progressbar',
              default=None,
              callback=validate_progressbar)
@click.option('--plan',
              help='Plan translations into a queue instead of processing them npw',
              is_flag=True,
              default=False)
@click.option('--broker-url',
              help='Celery broker URL (only needed when planning translation)',
              default='redis://localhost:6379')
def translate(syslog_address, syslog_port, syslog_facility, **options):
    # Configure Syslog handler
    add_syslog_handler(syslog_address, syslog_port, syslog_facility)
    add_stdout_handler(options['stdout_loglevel'])
    # Configure celery app broker url globally
    celery_app.conf.broker_url = options['broker_url']
    # We setup the translator. Etheir if the translation is done now
    # or later, we need initialize the interpreter (Argos, Apertium, ...)
    es_translator = EsTranslator(options)
    es_translator.start()
        


@click.command()
@click.option('--broker-url', default='redis://redis', help='Celery broker URL')
@click.option('--concurrency', default=1, help='Number of concurrent workers')
@click.option('--stdout-loglevel',
              help='Change the default log level for stdout error handler',
              default='ERROR',
              callback=validate_loglevel)
def tasks(broker_url, concurrency, stdout_loglevel):
    """Starts a Celery worker."""
    celery_app.conf.broker_url = broker_url
    argv = [
        'worker',
        '--concurrency',
        concurrency,
        '--loglevel',
        stdout_loglevel]
    celery_app.worker_main(argv)


@click.command()
@click.option('--data-dir',
              help='Path to the directory where to language model will be downloaded',
              type=click.Path(exists=True,
                              dir_okay=True,
                              writable=True,
                              readable=True),
              default=mkdtemp())
@click.option('--local', help='List pairs available locally',
              is_flag=True, default=False)
@click.option('--syslog-address', help='Syslog address', default='localhost')
@click.option('--syslog-port', help='Syslog port', default=514)
@click.option('--syslog-facility', help='Syslog facility', default='local7')
@click.option('--stdout-loglevel',
              help='Change the default log level for stdout error handler',
              default='ERROR',
              callback=validate_loglevel)
def pairs(
        data_dir,
        local,
        syslog_address,
        syslog_port,
        syslog_facility,
        **options):
    # Configure Syslog handler
    add_syslog_handler(syslog_address, syslog_port, syslog_facility)
    add_stdout_handler(options['stdout_loglevel'])
    # Only the data-dir is needed to construct the Apertium instance, then
    # we just need to print the pair
    Pairs(data_dir, local).print_pairs()


if __name__ == '__main__':
    translate()
