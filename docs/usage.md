---
icon: material/book-open-variant
---

# Usage

This guide covers how to use es-translator to translate documents in Elasticsearch.

## Quick Start

Translate documents from French to English:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en
```

## Installation

=== "pip"

    ```bash
    pip install es-translator
    ```

=== "Docker"

    ```bash
    docker run -it icij/es-translator es-translator --help
    ```

=== "From source"

    ```bash
    git clone https://github.com/icij/es-translator.git
    cd es-translator
    make install
    ```

### Optional: Install Apertium

Apertium is only required if you want to use the Apertium interpreter. es-translator works out of the box with Argos (the default).

```bash
wget https://apertium.projectjj.com/apt/install-nightly.sh -O - | sudo bash
sudo apt install apertium-all-dev
```

## Basic Translation

### Translate a Field

By default, es-translator translates the `content` field and stores results in `content_translated`:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en
```

### Translate a Different Field

To translate a different field (e.g., `title`):

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en \
  --source-field title \
  --target-field title_translated
```

### Filter Documents

Use Elasticsearch query strings to filter which documents to translate:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en \
  --query-string "type:article AND status:published"
```

### Force Re-translation

By default, es-translator skips already translated documents. To re-translate:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en \
  --force
```

## Choosing an Interpreter

es-translator supports two translation backends:

| Feature | Argos (default) | Apertium |
|---------|-----------------|----------|
| **Type** | Neural Machine Translation | Rule-based Translation |
| **Quality** | Higher quality | Good for related languages |
| **Speed** | Slower (ML models) | Faster |
| **Offline** | Yes (downloads models) | Yes (system packages) |
| **Languages** | ~30 languages | 40+ language pairs |
| **Intermediary** | Not supported | Supported |
| **Installation** | Automatic | Requires system packages |

### Using Argos (Default)

Argos provides neural machine translation with automatic model downloading:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en \
  --interpreter argos
```

### Using Apertium

Apertium provides rule-based translation, ideal for related languages:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language es \
  --target-language pt \
  --interpreter apertium
```

#### Intermediary Languages

When a direct translation pair isn't available, use an intermediary language:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language pt \
  --target-language en \
  --interpreter apertium \
  --intermediary-language es
```

#### List Available Pairs

```bash
# Show remotely available pairs
es-translator-pairs

# Show locally installed pairs
es-translator-pairs --local
```

## Performance Tuning

### Parallel Processing

Use multiple worker processes for faster translation:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en \
  --pool-size 4
```

### Large Datasets

For large datasets, increase the scroll timeout to prevent context loss:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en \
  --scan-scroll 30m
```

### Limit Content Length

Prevent issues with very large documents:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en \
  --max-content-length 10M
```

### Throttling

Add delay between translations to reduce Elasticsearch load:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en \
  --throttle 100  # 100ms delay
```

### GPU Acceleration

Argos supports GPU acceleration via CUDA for faster neural translation:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en \
  --device cuda
```

Available device options:

| Device | Description |
|--------|-------------|
| `auto` | Use CUDA if available, otherwise CPU (default) |
| `cuda` | Force GPU usage (requires CUDA) |
| `cpu` | Force CPU usage |

You can also set the device via environment variable:

```bash
export ES_TRANSLATOR_DEVICE=cuda
es-translator ...
```

!!! note "CUDA Requirements"
    GPU acceleration requires a CUDA-compatible GPU and the appropriate CUDA libraries installed. If CUDA is not available and `--device cuda` is specified, translation will fail. See [Install NVIDIA drivers on Ubuntu AWS instances](https://documentation.ubuntu.com/aws/aws-how-to/instances/install-nvidia-drivers/) for setup instructions.

## Distributed Translation

For very large datasets, distribute translation across multiple servers using Celery and Redis.

### Step 1: Plan the Translation

Queue documents for translation:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en \
  --broker-url "redis://redis:6379" \
  --plan
```

### Step 2: Start Workers

Start one or more workers to process the queue:

```bash
es-translator-tasks \
  --broker-url "redis://redis:6379" \
  --concurrency 2
```

### Using Docker for Workers

Run workers as a service with automatic restart:

```bash
docker run \
  --detach \
  --restart on-failure \
  --name es-translator-worker \
  icij/es-translator es-translator-tasks \
    --broker-url "redis://redis:6379" \
    --concurrency 2
```

## Testing & Debugging

### Dry Run

Test without saving to Elasticsearch:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en \
  --dry-run
```

### Debug Logging

Enable verbose logging:

```bash
es-translator \
  --url "http://localhost:9200" \
  --index my-index \
  --source-language fr \
  --target-language en \
  --stdout-loglevel DEBUG
```

## CLI Reference

### es-translator

Main command for translating documents.

```
es-translator [OPTIONS]

Options:
  -u, --url TEXT                  Elasticsearch URL
  -i, --index TEXT                Elasticsearch Index
  -r, --interpreter TEXT          Interpreter (argos or apertium)
  -s, --source-language TEXT      Source language [required]
  -t, --target-language TEXT      Target language [required]
  --intermediary-language TEXT    Intermediary language for indirect translation
  --source-field TEXT             Field to translate (default: content)
  --target-field TEXT             Field for translations (default: content_translated)
  -q, --query-string TEXT         Filter documents with query string
  -d, --data-dir PATH             Directory for language models
  --scan-scroll TEXT              Scroll duration (default: 5m)
  --dry-run                       Don't save to Elasticsearch
  -f, --force                     Re-translate existing translations
  --pool-size INTEGER             Number of parallel workers
  --pool-timeout INTEGER          Worker timeout in seconds
  --throttle INTEGER              Delay between translations (ms)
  --progressbar / --no-progressbar  Show progress bar
  --plan                          Queue for distributed translation
  --broker-url TEXT               Redis URL for distributed mode
  --max-content-length TEXT       Max content length (e.g., 10M, 1G)
  --device [cpu|cuda|auto]        Device for Argos translation (default: auto)
  --stdout-loglevel TEXT          Log level (DEBUG, INFO, WARNING, ERROR)
  --help                          Show help
```

### es-translator-tasks

Start Celery workers for distributed translation.

```
es-translator-tasks [OPTIONS]

Options:
  --broker-url TEXT       Redis URL
  --concurrency INTEGER   Number of concurrent workers
  --stdout-loglevel TEXT  Log level
  --help                  Show help
```

### es-translator-pairs

List available Apertium language pairs.

```
es-translator-pairs [OPTIONS]

Options:
  --data-dir PATH   Directory for language packs
  --local           Show only locally installed pairs
  --help            Show help
```
