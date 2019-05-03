# ES Translator

A lazy yet bulletproof machine translation tool for Elastichsearch.

```
$ python es_translator.py --help                                                                                                                                                                   
Usage: es_translator.py [OPTIONS]

Options:
  --url TEXT                    Elastichsearch URL
  --index TEXT                  Elastichsearch Index
  --source-language TEXT        Source language to translate from
  --target-language TEXT        Target language to translate to
  --intermediary-language TEXT  An intermediary language to use when no
                                translation is available between the source
                                and the target. If none is provided this will
                                be calculated automaticly.
  --source-field TEXT           Document field to translate
  --target-field TEXT           Document field to translate
  --query TEXT                  Search query string to filter result
  --data-dir TEXT               Path to the directory where to language model
                                will be downloaded
  --help                        Show this message and exit.
```
