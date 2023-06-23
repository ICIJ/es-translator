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