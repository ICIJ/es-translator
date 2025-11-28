"""Command-line interface for es-translator.

This module provides Click-based CLI commands for translating Elasticsearch documents,
managing translation workers, and listing available language pairs.
"""
import logging
import re
from tempfile import mkdtemp
from typing import Any, Optional

import click

from es_translator import EsTranslator

# Module from the same package
from es_translator.interpreters import Apertium, Argos
from es_translator.interpreters.apertium.pairs import Pairs
from es_translator.logger import add_stdout_handler, add_syslog_handler
from es_translator.tasks import app as celery_app


def validate_loglevel(ctx: click.Context, param: click.Parameter, value: Any) -> int:
    """Validate and convert log level parameter.

    Args:
        ctx: Click context.
        param: Click parameter.
        value: Log level string or integer.

    Returns:
        Log level as integer.

    Raises:
        click.BadParameter: If value is not a valid log level.
    """
    try:
        if isinstance(value, str):
            return getattr(logging, value)
        return int(value)
    except (AttributeError, ValueError):
        raise click.BadParameter(
            'must be a valid log level (CRITICAL, ERROR, WARNING, INFO, DEBUG or NOTSET)')


def validate_progressbar(ctx: click.Context, param: click.Parameter, value: Optional[bool]) -> bool:
    """Validate progressbar option.

    If no value given, activate progress bar only when stdout_loglevel > INFO (20).

    Args:
        ctx: Click context.
        param: Click parameter.
        value: Optional boolean value.

    Returns:
        True if progress bar should be shown.
    """
    return value if value is not None else ctx.params['stdout_loglevel'] > 20


def validate_interpreter(ctx: click.Context, param: click.Parameter, value: str) -> str:
    """Validate interpreter name parameter.

    Args:
        ctx: Click context.
        param: Click parameter.
        value: Interpreter name string.

    Returns:
        Validated interpreter name.

    Raises:
        click.BadParameter: If interpreter name is not valid.
    """
    interpreters = (Apertium, Argos, )
    for interpreter in interpreters:
        if value.upper() == interpreter.name.upper():
            return interpreter.name
    names = (interpreter.name for interpreter in interpreters)
    raise click.BadParameter(
        f'must be a valid interpreter name ({", ".join(names)})')


def validate_max_content_length(ctx: click.Context, param: click.Parameter, value: str) -> int:
    """Validate and convert max content length parameter.

    Accepts values like '100', '10K', '5M', '2G' and converts to bytes.

    Args:
        ctx: Click context.
        param: Click parameter.
        value: Content length string with optional K/M/G suffix.

    Returns:
        Content length in bytes as integer.

    Raises:
        click.BadParameter: If format is invalid.
    """
    if re.match('[0-9]+[KMG]?$', value):
        if value.endswith('K'):
            return int(value[:-1]) * 1024
        if value.endswith('M'):
            return int(value[:-1]) * 1024 ** 2
        if value.endswith('G'):
            return int(value[:-1]) * 1024 ** 3
        return int(value)
    else:
        raise click.BadParameter('max content length should be a number optionally followed by K or M or G')


@click.command()
@click.option('-u', '--url', help='Elastichsearch URL',
              default="http://localhost:9200")
@click.option('-i', '--index', help='Elastichsearch Index', default='local-datashare')
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
@click.option('-f',
              '--force',
              help='Override existing translation in Elasticsearch',
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
@click.option('--max-content-length',
              help="Max translated content length (<[0-9]+[KMG]?>) to avoid highlight errors"
                   "(see http://github.com/ICIJ/datashare/issues/1184)",
              default="19G",
              callback=validate_max_content_length)
def translate(syslog_address: str, syslog_port: int, syslog_facility: str, **options: Any) -> None:
    """Translate documents in an Elasticsearch index.

    Main command for translating documents using various interpreters (Argos, Apertium).
    Can run immediately or queue translations for later execution.

    Args:
        syslog_address: Syslog server address.
        syslog_port: Syslog server port.
        syslog_facility: Syslog facility name.
        **options: Additional options from Click decorators.
    """
    # Configure Syslog handler
    add_syslog_handler(syslog_address, syslog_port, syslog_facility)
    add_stdout_handler(options['stdout_loglevel'])
    # Configure celery app broker url globally
    celery_app.conf.broker_url = options['broker_url']
    # We setup the translator. Either if the translation is done now
    # or later, we need to initialize the interpreter (Argos, Apertium, ...)
    es_translator = EsTranslator(options)
    es_translator.start()



@click.command()
@click.option('--broker-url', default='redis://redis', help='Celery broker URL')
@click.option('--concurrency', default=1, help='Number of concurrent workers')
@click.option('--stdout-loglevel',
              help='Change the default log level for stdout error handler',
              default='ERROR',
              callback=validate_loglevel)
def tasks(broker_url: str, concurrency: int, stdout_loglevel: int) -> None:
    """Start a Celery worker for processing queued translations.

    Args:
        broker_url: Celery broker URL (e.g., 'redis://localhost:6379').
        concurrency: Number of concurrent worker processes.
        stdout_loglevel: Log level for stdout output.
    """
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
        data_dir: str,
        local: bool,
        syslog_address: str,
        syslog_port: int,
        syslog_facility: str,
        **options: Any) -> None:
    """List available Apertium language pairs.

    Args:
        data_dir: Directory for language pack storage.
        local: If True, list only locally installed pairs.
        syslog_address: Syslog server address.
        syslog_port: Syslog server port.
        syslog_facility: Syslog facility name.
        **options: Additional options from Click decorators.
    """
    # Configure Syslog handler
    add_syslog_handler(syslog_address, syslog_port, syslog_facility)
    add_stdout_handler(options['stdout_loglevel'])
    # Only the data-dir is needed to construct the Apertium instance, then
    # we just need to print the pair
    Pairs(data_dir, local).print_pairs()


if __name__ == '__main__':
    translate()
