import os
from typing import Any

from celery import Celery

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

app = Celery('EsTranslator', broker=REDIS_URL)
app.conf.task_default_queue = 'es_translator:default'


@app.task
def translate_document_task(
        translator_options: dict[str, Any], document_params: dict[str, Any]) -> None:
    """Celery task to translate a document.

    Args:
        translator_options (Dict[str, Any]): A dictionary of options for the translator.
        document_params (Dict[str, Any]): A dictionary of parameters to find the document.
    """
    from es_translator import EsTranslator
    # Initialize an EsTranslator with the options from the task
    es_translator = EsTranslator(translator_options)
    # Find the document using params
    document = es_translator.find_document(document_params)
    # Translate the document
    es_translator.translate_document(document)
