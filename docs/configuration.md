# Configuration

es-translator can be configured via command-line options or environment variables.

## Environment Variables

All CLI defaults can be overridden via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `ES_TRANSLATOR_ELASTICSEARCH_URL` | Elasticsearch URL | `http://localhost:9200` |
| `ES_TRANSLATOR_ELASTICSEARCH_INDEX` | Default index name | `local-datashare` |
| `ES_TRANSLATOR_REDIS_URL` | Redis URL for Celery | `redis://localhost:6379` |
| `ES_TRANSLATOR_BROKER_URL` | Celery broker URL | Same as `ES_TRANSLATOR_REDIS_URL` |
| `ES_TRANSLATOR_INTERPRETER` | Default interpreter | `ARGOS` |
| `ES_TRANSLATOR_SOURCE_FIELD` | Default source field | `content` |
| `ES_TRANSLATOR_TARGET_FIELD` | Default target field | `content_translated` |
| `ES_TRANSLATOR_MAX_CONTENT_LENGTH` | Max content length | `19G` |
| `ES_TRANSLATOR_POOL_SIZE` | Default worker pool size | `1` |
| `ES_TRANSLATOR_POOL_TIMEOUT` | Worker timeout (seconds) | `1800` |
| `ES_TRANSLATOR_SCAN_SCROLL` | Elasticsearch scroll duration | `5m` |
| `ES_TRANSLATOR_SYSLOG_ADDRESS` | Syslog server address | `localhost` |
| `ES_TRANSLATOR_SYSLOG_PORT` | Syslog server port | `514` |
| `ES_TRANSLATOR_SYSLOG_FACILITY` | Syslog facility | `local7` |

## Usage Examples

### Docker with Environment Variables

```bash
docker run \
  -e ES_TRANSLATOR_ELASTICSEARCH_URL="http://elasticsearch:9200" \
  -e ES_TRANSLATOR_REDIS_URL="redis://redis:6379" \
  icij/es-translator es-translator \
    --index my-index \
    --source-language fr \
    --target-language en
```

### Docker Compose

```yaml
services:
  es-translator:
    image: icij/es-translator
    environment:
      ES_TRANSLATOR_ELASTICSEARCH_URL: http://elasticsearch:9200
      ES_TRANSLATOR_REDIS_URL: redis://redis:6379
      ES_TRANSLATOR_INTERPRETER: ARGOS
      ES_TRANSLATOR_POOL_SIZE: 4
```

### Shell Export

```bash
export ES_TRANSLATOR_ELASTICSEARCH_URL="http://localhost:9200"
export ES_TRANSLATOR_INTERPRETER="ARGOS"

es-translator --index my-index -s fr -t en
```

## CLI Options Reference

### es-translator

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `-u, --url` | `ES_TRANSLATOR_ELASTICSEARCH_URL` | `http://localhost:9200` | Elasticsearch URL |
| `-i, --index` | `ES_TRANSLATOR_ELASTICSEARCH_INDEX` | `local-datashare` | Elasticsearch index |
| `-r, --interpreter` | `ES_TRANSLATOR_INTERPRETER` | `ARGOS` | Translation interpreter |
| `-s, --source-language` | - | *required* | Source language code |
| `-t, --target-language` | - | *required* | Target language code |
| `--intermediary-language` | - | - | Intermediary language (Apertium) |
| `--source-field` | `ES_TRANSLATOR_SOURCE_FIELD` | `content` | Field to translate |
| `--target-field` | `ES_TRANSLATOR_TARGET_FIELD` | `content_translated` | Field for translations |
| `-q, --query-string` | - | - | Elasticsearch query filter |
| `-d, --data-dir` | - | temp directory | Language model directory |
| `--scan-scroll` | `ES_TRANSLATOR_SCAN_SCROLL` | `5m` | Scroll duration |
| `--dry-run` | - | `false` | Don't save to Elasticsearch |
| `-f, --force` | - | `false` | Re-translate existing |
| `--pool-size` | `ES_TRANSLATOR_POOL_SIZE` | `1` | Parallel workers |
| `--pool-timeout` | `ES_TRANSLATOR_POOL_TIMEOUT` | `1800` | Worker timeout (s) |
| `--throttle` | - | `0` | Delay between translations (ms) |
| `--progressbar` | - | auto | Show progress bar |
| `--plan` | - | `false` | Queue for distributed mode |
| `--broker-url` | `ES_TRANSLATOR_BROKER_URL` | `redis://localhost:6379` | Celery broker URL |
| `--max-content-length` | `ES_TRANSLATOR_MAX_CONTENT_LENGTH` | `19G` | Max content length |
| `--stdout-loglevel` | - | `ERROR` | Log level |
| `--syslog-address` | `ES_TRANSLATOR_SYSLOG_ADDRESS` | `localhost` | Syslog address |
| `--syslog-port` | `ES_TRANSLATOR_SYSLOG_PORT` | `514` | Syslog port |
| `--syslog-facility` | `ES_TRANSLATOR_SYSLOG_FACILITY` | `local7` | Syslog facility |

### es-translator-tasks

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `--broker-url` | `ES_TRANSLATOR_BROKER_URL` | `redis://localhost:6379` | Celery broker URL |
| `--concurrency` | `ES_TRANSLATOR_POOL_SIZE` | `1` | Concurrent workers |
| `--stdout-loglevel` | - | `ERROR` | Log level |

### es-translator-pairs

| Option | Default | Description |
|--------|---------|-------------|
| `--data-dir` | temp directory | Language pack directory |
| `--local` | `false` | Show local pairs only |
| `--stdout-loglevel` | `ERROR` | Log level |

## Content Length Format

The `--max-content-length` option accepts values with size suffixes:

| Format | Value |
|--------|-------|
| `100` | 100 bytes |
| `10K` | 10 KB (10,240 bytes) |
| `5M` | 5 MB (5,242,880 bytes) |
| `1G` | 1 GB (1,073,741,824 bytes) |
| `19G` | 19 GB (default for Datashare) |

## Log Levels

Available log levels for `--stdout-loglevel`:

| Level | Description |
|-------|-------------|
| `DEBUG` | Detailed debugging information |
| `INFO` | General operational messages |
| `WARNING` | Warning messages |
| `ERROR` | Error messages only (default) |
| `CRITICAL` | Critical errors only |

## Language Codes

es-translator accepts both ISO 639-1 (2-letter) and ISO 639-3 (3-letter) language codes:

| Language | 2-letter | 3-letter |
|----------|----------|----------|
| English | `en` | `eng` |
| French | `fr` | `fra` |
| Spanish | `es` | `spa` |
| German | `de` | `deu` |
| Portuguese | `pt` | `por` |
| Italian | `it` | `ita` |

Both formats are accepted and normalized internally.
