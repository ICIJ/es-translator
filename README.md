# ES Translator

[![CircleCI](https://circleci.com/gh/ICIJ/es-translator.svg?style=svg)](https://circleci.com/gh/ICIJ/es-translator)

A lazy yet bulletproof machine translation tool for Elastichsearch.

```
Usage: es-translator [OPTIONS]

Options:
  --url TEXT                    Elastichsearch URL  [required]
  --index TEXT                  Elastichsearch Index  [required]
  --interpreter TEXT            Interpreter to use to perform the translation
  --source-language TEXT        Source language to translate from  [required]
  --target-language TEXT        Target language to translate to  [required]
  --intermediary-language TEXT  An intermediary language to use when no
                                translation is available between the source
                                and the target. If none is provided this will
                                be calculated automatically.
  --source-field TEXT           Document field to translate
  --target-field TEXT           Document field where the translations are
                                stored
  --query-string TEXT           Search query string to filter result
  --data-dir PATH               Path to the directory where to language model
                                will be downloaded
  --scan-scroll TEXT            Scroll duration (set to higher value if you're
                                processing a lot of documents)
  --dry-run                     Don't save anything in Elasticsearch
  --pool-size INTEGER           Number of parallel processes to start
  --pool-timeout INTEGER        Timeout to add a translation
  --syslog-address TEXT         Syslog address
  --syslog-port INTEGER         Syslog port
  --syslog-facility TEXT        Syslog facility
  --stdout-loglevel TEXT        Change the default log level for stdout error
                                handler
  --help                        Show this message and exit.
```

## Installation (Ubuntu)

Install Apertium:

```
wget https://apertium.projectjj.com/apt/install-nightly.sh -O - | sudo bash
sudo apt install apertium-all-dev
```

Create a Virtualenv and install Pip packages with Pipenv:

```
sudo apt install pipenv
make install
```

On Ubuntu 22.04 some additional packages might be needed if you use the version from Ubuntu's repository:

```
sudo apt install cg3 apertium-get apertium-lex-tools
```


## Installation (Docker)

Nothing to do as long as you have Docker on your system:

```
docker run -it icij/es-translator python es_translator.py --help
```

## Examples

Translates documents from French to Spanish on a local Elasticsearch. The translated field is `content` (the default).

```bash
python es_translator.py --url "http://localhost:9200" --index my-index --source-language fr --target-language es
```

Translates documents from French to English on a local Elasticsearch using Argos Translate:

```bash
python es_translator.py --url "http://localhost:9200" --index my-index --source-language fr --target-language en --interpreter argos
```

To translate the `title` field we could do:

```bash
pipenv es_translator.py --url "http://localhost:9200" --index my-index --source-language fr --target-language es --source-field title
```

Translates documents from English to Spanish on a local Elasticsearch using 4 threads:

```bash
python es_translator.py --url "http://localhost:9200" --index my-index --source-language en --target-language es --pool-size 4
```

Translates documents from Portuguese to English, using an intermediary language (Apertium doesn't offer this translation pair):

```bash
python es_translator.py --url "http://localhost:9200" --index my-index --source-language pt --intermediary-language es --target-language en
```
