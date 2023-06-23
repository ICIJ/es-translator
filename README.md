# ES Translator [![](https://img.shields.io/github/actions/workflow/status/icij/es-translator/main.yml)](https://github.com/ICIJ/es-translator/actions) [![](https://img.shields.io/pypi/pyversions/es-translator)](https://pypi.org/project/es-translator/) 

A lazy yet bulletproof machine translation tool for Elastichsearch.

## Installation (Ubuntu)

Install Apertium:

```bash
wget https://apertium.projectjj.com/apt/install-nightly.sh -O - | sudo bash
sudo apt install apertium-all-dev
```

Then install es-translator with pip:

```bash
python3 -m pip install --user es-translator
```

## Installation (Docker)

Nothing to do as long as you have Docker on your system:

```
docker run -it icij/es-translator es-translator --help
```

## Usage

The primarly command from EsTranslator to translate documents is `es-translator`:


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

Learn more about how to use this command in the [Usage Documentation](https://icij.github.io/es-translator/usage/).

## API

You can explore the [API Documentation](https://icij.github.io/es-translator/api/) for more information.

## Contributing

Contributions are welcome! If you encounter any issues or have suggestions for improvements, please open an issue on the [GitHub repository](https://github.com/icij/es-translator). If you're willing to help, check the page about [how to contribute](https://icij.github.io/es-translator/contributing/) to this project.

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/icij/es-translator/blob/main/LICENSE.md) file for more details.

