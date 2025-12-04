---
icon: material/sitemap
---

# Architecture

This page explains es-translator's architecture and how its components work together.

## Overview

es-translator is a Python application that reads documents from Elasticsearch, translates them using a pluggable interpreter system, and writes the translations back.

```
┌────────────────────────────────────────────────────────────────────┐
│                           es-translator                            │
│  ┌───────────────┐    ┌──────────────────┐    ┌─────────────────┐  │
│  │  EsTranslator │───▶│    Interpreter   │───▶│  TranslatedHit  │  │
│  │     (core)    │    │ (Argos/Apertium) │    │    (result)     │  │
│  └───────────────┘    └──────────────────┘    └─────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
         │                                          │
         ▼                                          ▼
┌─────────────────┐                      ┌─────────────────┐
│  Elasticsearch  │◀─────────────────────│  Elasticsearch  │
│    (read)       │                      │    (write)      │
└─────────────────┘                      └─────────────────┘
```

## Core Components

### EsTranslator

The main orchestrator class (`es_translator/es_translator.py`) that:

- Connects to Elasticsearch
- Configures and executes search queries
- Manages worker pools for parallel processing
- Coordinates the translation pipeline

```python
from es_translator import EsTranslator

translator = EsTranslator({
    'url': 'http://localhost:9200',
    'index': 'my-index',
    'source_language': 'fr',
    'target_language': 'en',
    'interpreter': 'ARGOS',
    ...
})
translator.start()
```

### Interpreters

Interpreters are pluggable translation backends. All interpreters inherit from `AbstractInterpreter`:

```
AbstractInterpreter
├── Argos      (Neural MT via argostranslate)
└── Apertium   (Rule-based MT via apertium)
```

Each interpreter implements:

- `translate(text)` - Translate text from source to target language
- `is_pair_available` - Check if the language pair is supported
- Language code conversion (ISO 639-1/639-3)

### TranslatedHit

Wraps Elasticsearch document hits (`es_translator/es.py`) and handles:

- Reading source content from documents
- Managing translation results
- Checking for existing translations
- Saving updated documents back to Elasticsearch

## Processing Modes

### Instant Mode (Default)

Documents are translated immediately as they're retrieved:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Scan     │────▶│  Translate  │────▶│    Save     │
│  (scroll)   │     │  (parallel) │     │   (bulk)    │
└─────────────┘     └─────────────┘     └─────────────┘
```

```bash
es-translator --url ... --index ... -s fr -t en
```

### Planned Mode (Distributed)

Documents are queued for later processing via Celery:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Planning Phase                          │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐        │
│  │    Scan     │────▶│   Queue     │────▶│    Redis    │        │
│  │  (scroll)   │     │   Tasks     │     │   (broker)  │        │
│  └─────────────┘     └─────────────┘     └─────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Execution Phase                          │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐        │
│  │   Worker    │────▶│  Translate  │────▶│    Save     │        │
│  │  (Celery)   │     │             │     │             │        │
│  └─────────────┘     └─────────────┘     └─────────────┘        │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐        │
│  │   Worker    │────▶│  Translate  │────▶│    Save     │        │
│  │  (Celery)   │     │             │     │             │        │
│  └─────────────┘     └─────────────┘     └─────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# Plan
es-translator --url ... --index ... -s fr -t en --broker-url redis://... --plan

# Execute
es-translator-tasks --broker-url redis://... --concurrency 4
```

## Parallel Processing

es-translator uses Python's `multiprocessing` module for parallel translation:

```
┌───────────────────────────────────────────────────────────────┐
│                        Main Process                           │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                   JoinableQueue                         │  │
│  │  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐       │  │
│  │  │doc1│ │doc2│ │doc3│ │doc4│ │doc5│ │doc6│ │... │       │  │
│  │  └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘       │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
         │           │           │           │
         ▼           ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ Worker  │ │ Worker  │ │ Worker  │ │ Worker  │
    │   1     │ │   2     │ │   3     │ │   4     │
    └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

Configure with `--pool-size`:

```bash
es-translator --pool-size 4 ...
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Core** | Python 3.9+ | Main application |
| **CLI** | Click | Command-line interface |
| **Search** | elasticsearch-dsl | Elasticsearch queries |
| **Neural MT** | argostranslate | Argos interpreter |
| **Rule-based MT** | Apertium (system) | Apertium interpreter |
| **Task Queue** | Celery | Distributed processing |
| **Message Broker** | Redis | Task queue backend |
| **Progress** | Rich | Terminal progress bars |
| **Logging** | coloredlogs | Colored log output |

## Data Flow

### Document Translation Flow

```
1. Search
   └── Query Elasticsearch with scroll API
       └── Retrieve batch of documents

2. Queue
   └── Add documents to processing queue
       └── Workers pick up documents

3. Translate
   └── Worker extracts source content
       └── Interpreter translates text
           └── Create translation result

4. Save
   └── Update document with translation
       └── Write back to Elasticsearch
```

### Translation Result Format

Documents are updated with a translation array:

```json
{
  "content": "Bonjour le monde",
  "content_translated": [
    {
      "translator": "ARGOS",
      "source_language": "FRENCH",
      "target_language": "ENGLISH",
      "content": "Hello world"
    }
  ]
}
```

Multiple translations (different language pairs) are appended to the array.

## Configuration

### Environment Variables

All CLI defaults can be overridden via environment variables:

```bash
export ES_TRANSLATOR_ELASTICSEARCH_URL="http://elasticsearch:9200"
export ES_TRANSLATOR_REDIS_URL="redis://redis:6379"
export ES_TRANSLATOR_INTERPRETER="ARGOS"
```

See [Configuration](configuration.md) for the complete list.

### Module Structure

```
es_translator/
├── __init__.py           # Package exports
├── es_translator.py      # Main EsTranslator class
├── es.py                 # TranslatedHit class
├── cli.py                # Click CLI commands
├── config.py             # Configuration defaults
├── worker.py             # Translation worker
├── tasks.py              # Celery tasks
├── logger.py             # Logging setup
├── alpha.py              # Language code utilities
├── symlink.py            # File utilities
└── interpreters/
    ├── __init__.py
    ├── abstract.py       # AbstractInterpreter base class
    ├── argos/
    │   ├── __init__.py
    │   └── argos.py      # Argos interpreter
    └── apertium/
        ├── __init__.py
        ├── apertium.py   # Apertium interpreter
        ├── repository.py # Package management
        └── pairs.py      # Language pairs listing
```

## Error Handling

### Exception Hierarchy

```
Exception
├── InvalidLanguageCode      # Invalid language code
├── ApertiumNotInstalledError # Apertium not available
├── PackageNotFoundError     # Repository package not found
├── PairPackageNotFoundError # Language pair not available
├── ArgosPairNotAvailable    # Argos pair not supported
└── FatalTranslationException # Unrecoverable error
```

### Worker Error Recovery

Workers handle errors gracefully:

- **Elasticsearch errors**: Logged and marked as fatal (stops processing)
- **Translation errors**: Logged and skipped (continues with next document)
- **Timeout errors**: Logged and retried

## Extending es-translator

### Adding a New Interpreter

1. Create a new class inheriting from `AbstractInterpreter`:

```python
from es_translator.interpreters.abstract import AbstractInterpreter

class MyInterpreter(AbstractInterpreter):
    name = 'MY_INTERPRETER'

    def translate(self, text_input: str) -> str:
        # Your translation logic
        return translated_text
```

2. Register in `es_translator/interpreters/__init__.py`

3. Add to CLI validation in `es_translator/cli.py`
