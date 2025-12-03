# API Reference

Welcome to the API reference for EsTranslator. This section provides detailed information about the classes, methods, and attributes available in the EsTranslator library.

## Core

::: es_translator.EsTranslator
    handler: python
    options:
      show_root_heading: true

## Interpreters

EsTranslator supports multiple translation backends (interpreters). Each interpreter has its own strengths and supported language pairs.

### Argos

Argos Translate is a neural machine translation library that provides high-quality translations using offline models.

::: es_translator.interpreters.Argos
    handler: python
    options:
      show_root_heading: true

### Apertium

Apertium is a rule-based machine translation platform that supports a wide variety of language pairs, especially for related languages.

::: es_translator.interpreters.Apertium
    handler: python
    options:
      show_root_heading: true

## Repository Management

::: es_translator.interpreters.apertium.repository.ApertiumRepository
    handler: python
    options:
      show_root_heading: true