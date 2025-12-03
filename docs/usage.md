## Choosing an Interpreter

EsTranslator supports two translation backends (interpreters):

| Feature | Argos (default) | Apertium |
|---------|-----------------|----------|
| **Type** | Neural Machine Translation | Rule-based Machine Translation |
| **Quality** | Generally higher quality | Good for related languages |
| **Speed** | Slower (uses ML models) | Faster |
| **Offline** | Yes (downloads models) | Yes (uses system packages) |
| **Languages** | ~30 languages | 40+ language pairs |
| **Intermediary** | Not supported | Supported |
| **Installation** | Automatic via pip | Requires system packages |

### When to use Argos

- You need high-quality translations
- You're translating between common language pairs
- You don't need intermediary language support

### When to use Apertium

- You're translating between related languages (e.g., Spanish-Portuguese)
- You need intermediary language support for indirect translations
- You need faster translation speed
- You're working with less common language pairs

To list available Apertium language pairs:

```bash
es-translator-pairs --local   # Show locally installed pairs
es-translator-pairs           # Show all available pairs (remote)
```

## Commands

### `es-translator`

This is the primary command from EsTranslator to translate documents.

```
Usage: es-translator [OPTIONS]

Options:
  -u, --url TEXT                  Elasticsearch URL
  -i, --index TEXT                Elasticsearch Index
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
  -d, --data-dir PATH             Path to the directory where the language
                                  model will be downloaded
  --scan-scroll TEXT              Scroll duration (set to higher value if
                                  you're processing a lot of documents)
  --dry-run                       Don't save anything in Elasticsearch
  -f, --force                     Override existing translation in
                                  Elasticsearch
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
                                  processing them now
  --broker-url TEXT               Celery broker URL (only needed when planning
                                  translation)
  --max-content-length TEXT       Max translated content length
                                  (<[0-9]+[KMG]?>) to avoid highlight
                                  errors(see http://github.com/ICIJ/datashare/
                                  issues/1184)
  --help                          Show this message and exit.
```

### `es-translator-tasks`

This command allows you to run es-translator workers with Celery. This is particularly useful when you
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
  --concurrency 1
```

You can run this command as many server as you want. In practice, we start it directly with a detached Docker container
so the task run as a service and can restart automaticaly in case of failure:

```bash
sudo docker run \
  --privileged \
  --interactive \
  --tty \
  --detach \
  --restart on-failure \
  --name es-translator-tasks \
  icij/es-translator es-translator-tasks \
    --broker-url "redis://redis:6379" \
    --concurrency 1
```

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis URL for Celery broker | `redis://localhost:6379/0` |

### Performance Tuning

- **`--pool-size`**: Increase for faster translation on multi-core systems. Each worker process handles one document at a time.
- **`--scan-scroll`**: Increase (e.g., `10m`, `30m`) when processing large datasets to prevent Elasticsearch scroll timeout.
- **`--max-content-length`**: Limit translated content length to avoid Elasticsearch highlighting issues. Accepts values like `1M`, `10M`, `1G`.
- **`--throttle`**: Add delay between translations (in ms) to reduce load on Elasticsearch.

## Troubleshooting

### Common Issues

#### "The pair is not available"

This error occurs when the requested language pair is not supported by the interpreter.

**For Argos:**

- Check available pairs: Argos automatically downloads required language models
- Ensure you have internet connectivity for the first run

**For Apertium:**

- List available pairs: `es-translator-pairs`
- Try using an intermediary language: `--intermediary-language es`

#### Elasticsearch scroll context timeout

When processing large datasets, you may see errors about lost scroll context.

**Solutions:**

1. Increase scroll duration: `--scan-scroll 30m`
2. Use planned translation mode with `--plan` to process documents individually
3. Reduce `--pool-size` to process fewer documents simultaneously

#### Memory issues with large documents

Large documents can cause memory issues, especially with Argos.

**Solutions:**

1. Limit content length: `--max-content-length 10M`
2. Reduce `--pool-size` to limit concurrent translations
3. Use Apertium interpreter which is more memory-efficient

#### Translation taking too long

**Solutions:**

1. Increase `--pool-size` for parallel processing
2. Use Apertium interpreter (faster but may have lower quality)
3. Filter documents with `--query-string` to process only what's needed
4. Use `--dry-run` first to test without saving

#### Docker container cannot connect to Elasticsearch

When running es-translator in Docker, it may not be able to reach Elasticsearch on `localhost`.

**Solutions:**

1. Use host network mode: `docker run --network host ...`
2. Use the host's IP address instead of `localhost`
3. Use Docker's special DNS name: `host.docker.internal` (on Docker Desktop)

### Debug Mode

To enable detailed logging for troubleshooting:

```bash
es-translator \
  --stdout-loglevel DEBUG \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en
```

### Dry Run Mode

Test your configuration without modifying Elasticsearch:

```bash
es-translator \
  --dry-run \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en
```
