"""Configuration management for es-translator.

This module provides centralized configuration with environment variable support.
All configuration values can be overridden via environment variables.
"""

import os

# Elasticsearch configuration
ELASTICSEARCH_URL = os.environ.get('ES_TRANSLATOR_ELASTICSEARCH_URL', 'http://localhost:9200')
ELASTICSEARCH_INDEX = os.environ.get('ES_TRANSLATOR_ELASTICSEARCH_INDEX', 'local-datashare')

# Redis/Celery configuration
REDIS_URL = os.environ.get('ES_TRANSLATOR_REDIS_URL', 'redis://localhost:6379')
BROKER_URL = os.environ.get('ES_TRANSLATOR_BROKER_URL', REDIS_URL)

# Translation defaults
DEFAULT_INTERPRETER = os.environ.get('ES_TRANSLATOR_INTERPRETER', 'ARGOS')
DEFAULT_SOURCE_FIELD = os.environ.get('ES_TRANSLATOR_SOURCE_FIELD', 'content')
DEFAULT_TARGET_FIELD = os.environ.get('ES_TRANSLATOR_TARGET_FIELD', 'content_translated')
DEFAULT_MAX_CONTENT_LENGTH = os.environ.get('ES_TRANSLATOR_MAX_CONTENT_LENGTH', '19G')

# Device configuration (for Argos neural translation)
# Options: 'cpu', 'cuda', 'auto'
DEFAULT_DEVICE = os.environ.get('ES_TRANSLATOR_DEVICE', 'auto')

# Worker configuration
DEFAULT_POOL_SIZE = int(os.environ.get('ES_TRANSLATOR_POOL_SIZE', '1'))
DEFAULT_POOL_TIMEOUT = int(os.environ.get('ES_TRANSLATOR_POOL_TIMEOUT', str(60 * 30)))
DEFAULT_SCAN_SCROLL = os.environ.get('ES_TRANSLATOR_SCAN_SCROLL', '5m')

# Logging configuration
DEFAULT_SYSLOG_ADDRESS = os.environ.get('ES_TRANSLATOR_SYSLOG_ADDRESS', 'localhost')
DEFAULT_SYSLOG_PORT = int(os.environ.get('ES_TRANSLATOR_SYSLOG_PORT', '514'))
DEFAULT_SYSLOG_FACILITY = os.environ.get('ES_TRANSLATOR_SYSLOG_FACILITY', 'local7')
