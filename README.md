# ES Translator [![](https://img.shields.io/github/actions/workflow/status/icij/es-translator/main.yml)](https://github.com/ICIJ/es-translator/actions) [![](https://img.shields.io/pypi/pyversions/es-translator)](https://pypi.org/project/es-translator/)

A lazy yet bulletproof machine translation tool for Elasticsearch.

## Installation

### pip

```bash
pip install es-translator
```

### Docker

```bash
docker run -it icij/es-translator es-translator --help
```

## Quick Start

Translate documents from French to English:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en
```

## Features

- **Two translation engines**: Argos (neural MT) and Apertium (rule-based MT)
- **Distributed processing**: Scale across multiple servers with Celery/Redis
- **Elasticsearch integration**: Direct read/write with scroll API support
- **Flexible filtering**: Translate specific documents using query strings
- **Incremental translation**: Skip already-translated documents

## Documentation

- [Usage Guide](https://icij.github.io/es-translator/usage/) - Complete usage instructions
- [Configuration](https://icij.github.io/es-translator/configuration/) - All options and environment variables
- [Datashare Integration](https://icij.github.io/es-translator/datashare/) - Using with ICIJ's Datashare
- [Architecture](https://icij.github.io/es-translator/architecture/) - How es-translator works
- [API Reference](https://icij.github.io/es-translator/api/) - Python API documentation

## Contributing

Contributions are welcome! See our [Contributing Guide](https://icij.github.io/es-translator/contributing/) for details.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE.md) for details.
