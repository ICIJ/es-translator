# ES Translator

[![CircleCI](https://circleci.com/gh/ICIJ/es-translator.svg?style=svg)](https://circleci.com/gh/ICIJ/es-translator)

A lazy yet bulletproof machine translation tool for Elastichsearch.

```
$ python es_translator.py --help                                                                                                                                                                   
Usage: es_translator.py [OPTIONS]

Options:
  --url TEXT                    Elastichsearch URL  [required]
  --index TEXT                  Elastichsearch Index  [required]
  --source-language TEXT        Source language to translate from  [required]
  --target-language TEXT        Target language to translate to  [required]
  --intermediary-language TEXT  An intermediary language to use when no
                                translation is available between the source
                                and the target. If none is provided this will
                                be calculated automaticly.
  --source-field TEXT           Document field to translate
  --target-field TEXT           Document field to translate
  --query TEXT                  Search query string to filter result
  --data-dir TEXT               Path to the directory where to language model
                                will be downloaded
  --scan-scroll TEXT            Scroll duration (set to higher value if you're
                                processing a lot of documents)
  --dry-run                     Don't save anything in Elasticsearch
  --pool-size INTEGER           Number of parallel processes to start
  --syslog-address TEXT         Syslog address
  --syslog-port INTEGER         Syslog port
  --syslog-facility TEXT        Syslog facility
  --help                        Show this message and exit.
```
