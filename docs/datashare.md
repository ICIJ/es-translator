# Using with Datashare

[Datashare](https://datashare.icij.org/) is ICIJ's open-source document analysis platform. es-translator was specifically designed to work with Datashare's Elasticsearch indices.

## Overview

Datashare stores extracted document content in Elasticsearch. es-translator can translate this content, making documents searchable in multiple languages.

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Datashare  │────▶│  Elasticsearch  │◀────│  es-translator  │
│  (extract)  │     │    (storage)    │     │   (translate)   │
└─────────────┘     └─────────────────┘     └─────────────────┘
```

## Document Structure

Datashare documents in Elasticsearch have this structure:

```json
{
  "content": "Original document text...",
  "contentTranslated": [
    {
      "content": "Translated text...",
      "source_language": "FRENCH",
      "target_language": "ENGLISH",
      "translator": "ARGOS"
    }
  ],
  "type": "Document",
  "path": "/path/to/file.pdf",
  ...
}
```

## Basic Usage

### Translate All Documents

Translate all documents from French to English:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index local-datashare \
  --source-language fr \
  --target-language en \
  --source-field content \
  --target-field contentTranslated
```

### Translate Only Documents (Skip Named Entities)

Datashare indices contain both documents and named entities. To translate only documents:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index local-datashare \
  --source-language fr \
  --target-language en \
  --source-field content \
  --target-field contentTranslated \
  --query-string "type:Document"
```

### Translate Specific Project

If you have multiple Datashare projects:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-project \
  --source-language fr \
  --target-language en \
  --source-field content \
  --target-field contentTranslated
```

## Docker Compose Setup

### With Datashare's Elasticsearch

If Datashare is running via Docker Compose, you can add es-translator as a service:

```yaml
version: '3.8'
services:
  datashare:
    image: icij/datashare
    ports:
      - "8080:8080"
    depends_on:
      - elasticsearch
      - redis

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.17.9
    environment:
      - discovery.type=single-node
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
    ports:
      - "9200:9200"

  redis:
    image: redis:6
    ports:
      - "6379:6379"

  # Add es-translator worker
  es-translator:
    image: icij/es-translator
    command: >
      es-translator-tasks
        --broker-url redis://redis:6379
        --concurrency 2
    depends_on:
      - redis
      - elasticsearch
    restart: on-failure
```

### Running a Translation Job

With this setup, plan translations from outside the container:

```bash
docker run --rm --network host icij/es-translator \
  es-translator \
    --url "http://localhost:9200" \
    --index local-datashare \
    --source-language fr \
    --target-language en \
    --source-field content \
    --target-field contentTranslated \
    --broker-url "redis://localhost:6379" \
    --plan
```

The `es-translator` service will automatically pick up and process the queued translations.

## Handling Large Datasets

Datashare projects can contain millions of documents. Here's how to handle them efficiently.

### Use Distributed Translation

For large projects, use the planning mode to distribute work:

```bash
# Step 1: Queue all documents
es-translator \
  --url "http://localhost:9200" \
  --index local-datashare \
  --source-language fr \
  --target-language en \
  --source-field content \
  --target-field contentTranslated \
  --broker-url "redis://redis:6379" \
  --query-string "type:Document" \
  --plan

# Step 2: Start multiple workers
es-translator-tasks --broker-url "redis://redis:6379" --concurrency 4
```

### Handle Content Length Limits

Datashare's highlighting feature has content length limits. Use `--max-content-length` to truncate translations:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index local-datashare \
  --source-language fr \
  --target-language en \
  --source-field content \
  --target-field contentTranslated \
  --max-content-length 19G
```

!!! note "Why 19G?"
    Datashare uses Lucene's highlighting which has internal limits. The `19G` value matches Datashare's expected maximum. See [datashare#1184](https://github.com/ICIJ/datashare/issues/1184) for details.

### Prevent Scroll Timeout

For very large indices, increase the scroll duration:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index local-datashare \
  --source-language fr \
  --target-language en \
  --source-field content \
  --target-field contentTranslated \
  --scan-scroll 30m
```

## Multiple Languages

### Sequential Translation

To translate documents into multiple target languages:

```bash
# French to English
es-translator \
  --url "http://localhost:9200" \
  --index local-datashare \
  --source-language fr \
  --target-language en \
  --source-field content \
  --target-field contentTranslated

# French to Spanish
es-translator \
  --url "http://localhost:9200" \
  --index local-datashare \
  --source-language fr \
  --target-language es \
  --source-field content \
  --target-field contentTranslated
```

Translations are appended to the `contentTranslated` array, so multiple translations can coexist.

## Troubleshooting

### "Connection refused" to Elasticsearch

If running es-translator in Docker and Elasticsearch is on the host:

```bash
# Use host network mode
docker run --network host icij/es-translator es-translator ...

# Or use host.docker.internal (Docker Desktop)
docker run icij/es-translator es-translator \
  --url "http://host.docker.internal:9200" ...
```

### Documents Not Being Translated

Check if documents are being filtered correctly:

```bash
# Test with dry-run and debug logging
es-translator \
  --url "http://localhost:9200" \
  --index local-datashare \
  --source-language fr \
  --target-language en \
  --source-field content \
  --target-field contentTranslated \
  --query-string "type:Document" \
  --dry-run \
  --stdout-loglevel DEBUG
```

### Existing Translations Not Overwritten

By default, es-translator skips already-translated documents. Use `--force` to re-translate:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index local-datashare \
  --source-language fr \
  --target-language en \
  --source-field content \
  --target-field contentTranslated \
  --force
```

## Environment Variables

When deploying with Datashare, you can configure es-translator via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `ES_TRANSLATOR_ELASTICSEARCH_URL` | Elasticsearch URL | `http://localhost:9200` |
| `ES_TRANSLATOR_ELASTICSEARCH_INDEX` | Default index | `local-datashare` |
| `ES_TRANSLATOR_REDIS_URL` | Redis URL for Celery | `redis://localhost:6379` |
| `ES_TRANSLATOR_INTERPRETER` | Default interpreter | `ARGOS` |
| `ES_TRANSLATOR_SOURCE_FIELD` | Default source field | `content` |
| `ES_TRANSLATOR_TARGET_FIELD` | Default target field | `content_translated` |
| `ES_TRANSLATOR_MAX_CONTENT_LENGTH` | Max content length | `19G` |
