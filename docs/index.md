# ES Translator [![](https://img.shields.io/github/actions/workflow/status/icij/es-translator/main.yml)](https://github.com/ICIJ/es-translator/actions) [![](https://img.shields.io/pypi/pyversions/es-translator)](https://pypi.org/project/es-translator/) 

A lazy yet bulletproof machine translation tool for Elastichsearch.

## Installation (Ubuntu)

Install Apertium:

```bash
wget https://apertium.projectjj.com/apt/install-nightly.sh -O - | sudo bash
sudo apt install apertium-all-dev
```

Then finally, install es-translator with pip:

```bash
python3 -m pip install --user es-translator
```

## Installation (Docker)

Nothing to do as long as you have Docker on your system:

```
docker run -it icij/es-translator poetry run es-translator --help
```

## Documentation

The documentation is generated from the docstrings in the code using the `mkdocstrings` plugin. It provides detailed information about the classes, methods, and attributes in the EsTranslator library.

You can explore the [API Documentation](api.md) for more information.

## Contributing

Contributions are welcome! If you encounter any issues or have suggestions for improvements, please open an issue on the [GitHub repository](https://github.com/icij/es-translator). If you're willing to help, check the page about [how to contribute](contributing.md) to this project.

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/icij/es-translator/blob/main/LICENSE.md) file for more details.
