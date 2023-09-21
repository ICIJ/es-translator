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

### Instant translation

Translates documents from French to Spanish on a local Elasticsearch. The translated field is `content` (the default).

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language es
```

Translates documents from French to English on a local Elasticsearch using Apertium:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en \
  --interpreter apertium
```

To translate the `title` field we could do:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language es \
  --source-field title
```

Translates documents from English to Spanish on a local Elasticsearch using 4 threads:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language en \
  --target-language es \
  --pool-size 4
```

Translates documents from Portuguese to English, using an intermediary language (Apertium doesn't offer this translation pair):

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --interpreter apertium \
  --source-language pt \
  --intermediary-language es \
  --target-language en
```

### Planned translation

This tools can be use to plan translation (ie. building a list of document to translate) which can be consume by
es-translator later, on one or several servers. This can be useful in two cases:

* You have a lot of big documents and EsTranslator loose the search context because it takes too long to translate a document
* You have a lot of documents and want to distribute the translation on several servers

To do so, you will have to follow two steps. We start with **planning the translation**:

```bash
es-translator \
  --url "http://localhost:9200" \
  --broker-url "redis://redis:6379" \
  --index my-index \
  --source-language fr \
  --target-language en \
  --pool-size 1 \
  --plan
```

What happends here? You can see we added two parameters to EsTranslator. First, `--broker-url` which is the URL of the 
remote Redis server we use to store the list and distribute it later. Second, `--plan` which simply tells EsTranslator 
to store the list of documents to translate (with all the given command arguments) in the broker.

When this command is done, we can proceed to **translate from the broker list**:

```bash
es-translator-tasks \
  --broker-url "redis://redis:6379" \
  --concurrency 1 \
  --plan
```

You can run this command as many server as you want. In practice, we start it directly with a detached Docker container
so the task run as a service and can restart automaticaly in case of failure:

```bash
sudo docker run \
  --privileged true \
  --interactive \
  --tty \
  --detach \
  --restart on-failure \
  --name es-translator-tasks \
  icij/es-translator es-translator-tasks \
    --broker-url "redis://redis:6379" \
    --concurrency 1 \
    --plan
```

