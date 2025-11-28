
from queue import Full
from time import sleep

from elasticsearch import ElasticsearchException

# Module from the same package
from es_translator.logger import logger


class FatalTranslationException(Exception):
    pass


def translation_worker(queue, shared_fatal_error):
    """
    Worker function that translates documents from the queue in parallel.

    Args:
        queue: JoinableQueue for retrieving documents to be translated.
        shared_fatal_error: Shared variable to track fatal errors.

    Notes:
        This function continuously retrieves documents from the queue and translates them until a fatal error occurs
        or the queue is empty. It handles different types of exceptions and updates the shared_fatal_error if needed.
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


def handle_elasticsearch_exception(error, index):
    # Handle Elasticsearch exception
    logger.error(f'An error occurred when saving doc {index.meta.id}')
    logger.error(error)


def handle_timeout_reached(pool_timeout):
    # Handle timeout reached
    logger.warning(f'Timeout reached ({pool_timeout}s).')


def handle_exception(error, hit):
    # Handle other exceptions
    logger.warning(f'Unable to translate doc {hit.meta.id}')
    logger.warning(error)
