## Commands
### `es-translator`

This is the primarly command from EsTranslator to translate documents.

```
Usage: es-translator [OPTIONS]

Options:
  -u, --url TEXT                  Elastichsearch URL
  -i, --index TEXT                Elastichsearch Index  [required]
  -r, --interpreter TEXT          Interpreter to use to perform the
                                  translation
  -s, --source-language TEXT      Source language to translate from
                                  [required]
  -t, --target-language TEXT      Target language to translate to  [required]
  --intermediary-language TEXT    An intermediary language to use when no
                                  translation is available between the source
                                  and the target. If none is provided this
                                  will be calculated automatically.
  --source-field TEXT             Document field to translate
  --target-field TEXT             Document field where the translations are
                                  stored
  -q, --query-string TEXT         Search query string to filter result
  -d, --data-dir PATH             Path to the directory where to language
                                  model will be downloaded
  --scan-scroll TEXT              Scroll duration (set to higher value if
                                  you're processing a lot of documents)
  --dry-run                       Don't save anything in Elasticsearch
  --pool-size INTEGER             Number of parallel processes to start
  --pool-timeout INTEGER          Timeout to add a translation
  --throttle INTEGER              Throttle between each translation (in ms)
  --syslog-address TEXT           Syslog address
  --syslog-port INTEGER           Syslog port
  --syslog-facility TEXT          Syslog facility
  --stdout-loglevel TEXT          Change the default log level for stdout
                                  error handler
  --progressbar / --no-progressbar
                                  Display a progressbar
  --plan                          Plan translations into a queue instead of
                                  processing them npw
  --broker-url TEXT               Celery broker URL (only needed when planning
                                  translation)
  --help                          Show this message and exit.
```

### `es-translator-tasks`

This command allows you to run es-translator workers with Celery. This is particulary useful when you
need to distribute the translation between different servers:

```
Usage: es-translator-tasks [OPTIONS]

  Starts a Celery worker.

Options:
  --broker-url TEXT       Celery broker URL
  --concurrency INTEGER   Number of concurrent workers
  --stdout-loglevel TEXT  Change the default log level for stdout error
                          handler
  --help                  Show this message and exit.
```

## Examples

Translates documents from French to Spanish on a local Elasticsearch. The translated field is `content` (the default).

```bash
poetry run es-translator --url "http://localhost:9200" --index my-index --source-language fr --target-language es
```

Translates documents from French to English on a local Elasticsearch using Apertium:

```bash
poetry run es-translator --url "http://localhost:9200" --index my-index --source-language fr --target-language en --interpreter apertium
```

To translate the `title` field we could do:

```bash
poetry run es-translator --url "http://localhost:9200" --index my-index --source-language fr --target-language es --source-field title
```

Translates documents from English to Spanish on a local Elasticsearch using 4 threads:

```bash
poetry run es-translator --url "http://localhost:9200" --index my-index --source-language en --target-language es --pool-size 4
```

Translates documents from Portuguese to English, using an intermediary language (Apertium doesn't offer this translation pair):

```bash
poetry run es-translator --url "http://localhost:9200" --index my-index --source-language pt --intermediary-language es --target-language en
```