---
icon: material/home
---

# ES Translator

A lazy yet bulletproof machine translation tool for Elasticsearch.

[![Build Status](https://img.shields.io/github/actions/workflow/status/icij/es-translator/main.yml)](https://github.com/ICIJ/es-translator/actions)
[![PyPI](https://img.shields.io/pypi/pyversions/es-translator)](https://pypi.org/project/es-translator/)
[![Docker](https://img.shields.io/docker/pulls/icij/es-translator)](https://hub.docker.com/r/icij/es-translator)

## What is es-translator?

es-translator reads documents from Elasticsearch, translates them using machine translation, and writes the translations back. It's designed for bulk translation of large document collections.

## Features

- **Two translation engines**
    - **Argos**: Neural machine translation with ~30 languages
    - **Apertium**: Rule-based translation with 40+ language pairs

- **Scalable processing**
    - Parallel workers for multi-core systems
    - Distributed mode with Celery/Redis for multi-server deployments

- **Elasticsearch integration**
    - Direct read/write with scroll API
    - Query string filtering
    - Incremental translation (skip already-translated docs)

## Quick Start

=== "pip"

    ```bash
    pip install es-translator

    es-translator \
      --url "http://localhost:9200" \
      --index my-index \
      --source-language fr \
      --target-language en
    ```

=== "Docker"

    ```bash
    docker run -it --network host icij/es-translator \
      es-translator \
        --url "http://localhost:9200" \
        --index my-index \
        --source-language fr \
        --target-language en
    ```

## Documentation

<div class="grid cards" markdown>

-   :material-book-open-variant:{ .lg .middle } **[Usage Guide](usage.md)**

    ---

    Complete guide to using es-translator: commands, options, and examples.

-   :material-cog:{ .lg .middle } **[Configuration](configuration.md)**

    ---

    All CLI options and environment variables.

-   :material-database:{ .lg .middle } **[Datashare Integration](datashare.md)**

    ---

    Using es-translator with ICIJ's Datashare platform.

-   :material-sitemap:{ .lg .middle } **[Architecture](architecture.md)**

    ---

    How es-translator works internally.

-   :material-api:{ .lg .middle } **[API Reference](api.md)**

    ---

    Python API documentation for programmatic usage.

-   :material-github:{ .lg .middle } **[Contributing](contributing.md)**

    ---

    How to contribute to es-translator.

</div>

## Links

- [GitHub Repository](https://github.com/icij/es-translator)
- [PyPI Package](https://pypi.org/project/es-translator/)
- [Docker Hub](https://hub.docker.com/r/icij/es-translator)

## License

MIT License - See [LICENSE](https://github.com/icij/es-translator/blob/main/LICENSE.md) for details.
