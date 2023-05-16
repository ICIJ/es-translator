
from time import sleep
from elasticsearch import Elasticsearch, ElasticsearchException
from queue import Full
# Module from the same package
from es_translator.logger import logger
from es_translator.es import TranslatedHit

class FatalTranslationException(Exception): pass

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
            es_translator, hit, index = queue.get(True)
            translate_document(es_translator, hit, index)
            sleep(es_translator.throttle / 1000)
        except ElasticsearchException as error:
            handle_elasticsearch_exception(error, index, hit)
            shared_fatal_error.value = error
        except Full:
            handle_timeout_reached(es_translator.pool_timeout)
        except Exception as error:
            handle_exception(error, index, hit)
        finally:
            queue.task_done()
    queue.close()


def translate_document(es_translator, hit, index):
    # Translate the document
    logger.info('Translating doc %s (%s)' % (index, hit.meta.id))
    translated_hit = TranslatedHit(hit, es_translator.source_field, es_translator.target_field)
    translated_hit.add_translation(es_translator.interpreter)
    logger.info('Translated doc %s (%s)' % (index, hit.meta.id))
    
    # Save the translated document if not in dry run mode
    if not es_translator.dry_run:
        client = Elasticsearch(es_translator.url)
        translated_hit.save(client)
        logger.info('Saved translation for doc %s (%s)' % (index, hit.meta.id))

def handle_elasticsearch_exception(error, index, hit):
    # Handle Elasticsearch exception
    logger.error('An error occurred when saving doc %s (%s)' % (index, hit.meta.id))
    logger.error(error)

def handle_timeout_reached(pool_timeout):
    # Handle timeout reached
    logger.warning('Timeout reached (%ss).' % pool_timeout)

def handle_exception(error, index, hit):
    # Handle other exceptions
    logger.warning('Unable to translate doc %s (%s)' % (index, hit.meta.id))
    logger.warning(error)
