# ES Translator [![](https://img.shields.io/github/actions/workflow/status/icij/es-translator/main.yml)](https://github.com/ICIJ/es-translator/actions) [![](https://img.shields.io/pypi/pyversions/es-translator)](https://pypi.org/project/es-translator/) 

A lazy yet bulletproof machine translation tool for Elasticsearch.

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

The primary command from EsTranslator to translate documents is `es-translator`:


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

Learn more about how to use this command in the [Usage Documentation](https://icij.github.io/es-translator/usage/).

## API

You can explore the [API Documentation](https://icij.github.io/es-translator/api/) for more information.


## Releasing a New Version

This section describes how to release a new version of es-translator. Only maintainers with publish access can perform releases.

### Prerequisites

* Push access to the GitHub repository
* PyPI credentials configured for Poetry (`poetry config pypi-token.pypi <your-token>`)
* Docker Hub credentials (for Docker image publishing)

### Release Process

#### 1. Ensure All Tests Pass

Before releasing, make sure all tests and linting checks pass:

```shell
make lint
make test
```

#### 2. Bump the Version

Use one of the semantic versioning targets to bump the version:

```shell
# For bug fixes (1.0.0 -> 1.0.1)
make patch

# For new features (1.0.0 -> 1.1.0)
make minor

# For breaking changes (1.0.0 -> 2.0.0)
make major
```

This will:

* Update the version in `pyproject.toml`
* Create a git commit with the message `build: bump to <version>`
* Create a git tag with the new version

Alternatively, set a specific version:

```shell
make set-version CURRENT_VERSION=1.2.3
```

#### 3. Push Changes and Tags

Push the commit and tag to GitHub:

```shell
git push origin master
git push origin --tags
```

#### 4. Publish to PyPI

Publish the package to PyPI:

```shell
make distribute
```

This builds the package and uploads it to PyPI using Poetry.

#### 5. Publish Docker Image (Optional)

To publish a new Docker image:

```shell
# First-time setup for multi-arch builds
make docker-setup-multiarch

# Build and push the Docker image
make docker-publish
```

This will build and push the image with both the version tag and `latest` tag to Docker Hub.

#### 6. Update Documentation

If documentation has changed, publish the updated docs:

```shell
make publish-doc
```

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

* **MAJOR** version for incompatible API changes
* **MINOR** version for new functionality in a backwards compatible manner
* **PATCH** version for backwards compatible bug fixes

### Makefile Targets Reference

| Target                                   | Description                          |
| ---------------------------------------- | ------------------------------------ |
| `make patch`                             | Bump patch version (x.x.X)           |
| `make minor`                             | Bump minor version (x.X.0)           |
| `make major`                             | Bump major version (X.0.0)           |
| `make set-version CURRENT_VERSION=x.x.x` | Set specific version                 |
| `make distribute`                        | Build and publish to PyPI            |
| `make docker-publish`                    | Build and push Docker image          |
| `make publish-doc`                       | Deploy documentation to GitHub Pages |

## Contributing

Contributions are welcome! If you encounter any issues or have suggestions for improvements, please open an issue on the [GitHub repository](https://github.com/icij/es-translator). If you're willing to help, check the page about [how to contribute](https://icij.github.io/es-translator/contributing/) to this project.

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/icij/es-translator/blob/main/LICENSE.md) file for more details.

