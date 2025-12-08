"""Worker module for parallel document translation.

This module provides worker functions for translating Elasticsearch documents
in parallel using a queue-based architecture.
"""

from multiprocessing import JoinableQueue
from multiprocessing.managers import ValueProxy
from queue import Full
from time import sleep
from typing import Any

from elasticsearch import ElasticsearchException
from elasticsearch_dsl.utils import ObjectBase

from es_translator.logger import logger


class FatalTranslationException(Exception):
    """Exception raised when a fatal error occurs during translation.

    This exception is used to signal that the translation process should
    stop due to an unrecoverable error.
    """


def translation_worker(queue: JoinableQueue, shared_fatal_error: ValueProxy[Any]) -> None:
    """Worker function that translates documents from the queue in parallel.

    Continuously retrieves documents from the queue and translates them
    until a fatal error occurs or the queue is empty.

    Args:
        queue: JoinableQueue for retrieving documents to be translated.
        shared_fatal_error: Shared variable to track fatal errors across workers.
    """
    while not shared_fatal_error.value:
        try:
            es_translator, hit = queue.get(True)
            es_translator.translate_document(hit)
            sleep(es_translator.throttle / 1000)
        except ElasticsearchException as error:
            handle_elasticsearch_exception(error, hit)
            shared_fatal_error.value = error
        except Full:
            handle_timeout_reached(es_translator.pool_timeout)
        except Exception as error:
            handle_exception(error, hit)
        finally:
            queue.task_done()
    queue.close()


def handle_elasticsearch_exception(error: ElasticsearchException, hit: ObjectBase) -> None:
    """Handle Elasticsearch exceptions during document save.

    Args:
        error: The Elasticsearch exception that occurred.
        hit: The document hit that failed to save.
    """
    logger.error(f'An error occurred when saving doc {hit.meta.id}')
    logger.error(error)


def handle_timeout_reached(pool_timeout: int) -> None:
    """Handle queue timeout events.

    Args:
        pool_timeout: The timeout value in seconds.
    """
    logger.warning(f'Timeout reached ({pool_timeout}s).')


def handle_exception(error: Exception, hit: ObjectBase) -> None:
    """Handle general exceptions during translation.

    Args:
        error: The exception that occurred.
        hit: The document hit that failed to translate.
    """
    logger.warning(f'Unable to translate doc {hit.meta.id}')
    logger.warning(error)
