---
icon: material/wrench
---

# Troubleshooting

Common issues and their solutions.

## Translation Errors

### "The pair is not available"

The requested language pair isn't supported by the interpreter.

=== "Argos"

    Argos automatically downloads language models. Ensure you have internet connectivity on first run.

    ```bash
    # Check if models download successfully
    es-translator \
      --url "http://localhost:9200" \
      --index test \
      --source-language fr \
      --target-language en \
      --stdout-loglevel DEBUG \
      --dry-run
    ```

=== "Apertium"

    List available pairs and use an intermediary language if needed:

    ```bash
    # List available pairs
    es-translator-pairs

    # Use intermediary language
    es-translator \
      --interpreter apertium \
      --source-language pt \
      --target-language en \
      --intermediary-language es \
      ...
    ```

### "Apertium is not installed"

Apertium requires system packages. Install them:

```bash
wget https://apertium.projectjj.com/apt/install-nightly.sh -O - | sudo bash
sudo apt install apertium-all-dev
```

Or use Argos instead (default, no installation required):

```bash
es-translator --interpreter argos ...
```

### Invalid Language Code

Use standard ISO 639-1 (2-letter) or ISO 639-3 (3-letter) codes:

| Language | Valid | Invalid |
|----------|-------|---------|
| English | `en`, `eng` | `english`, `EN` |
| French | `fr`, `fra` | `french`, `fre` |

## Elasticsearch Issues

### Connection Refused

Can't connect to Elasticsearch.

**Check Elasticsearch is running:**

```bash
curl http://localhost:9200
```

**Docker networking issues:**

```bash
# Use host network
docker run --network host icij/es-translator ...

# Or use host.docker.internal (Docker Desktop)
docker run icij/es-translator es-translator \
  --url "http://host.docker.internal:9200" ...
```

### Scroll Context Lost

For large datasets, the scroll context may expire.

**Increase scroll duration:**

```bash
es-translator --scan-scroll 30m ...
```

**Use planned mode for very large datasets:**

```bash
# Queue documents (no scroll needed during execution)
es-translator --plan --broker-url redis://... ...

# Process from queue
es-translator-tasks --broker-url redis://...
```

### Index Not Found

Verify the index exists:

```bash
curl http://localhost:9200/_cat/indices
```

## Performance Issues

### Translation Too Slow

**Increase parallel workers:**

```bash
es-translator --pool-size 4 ...
```

**Use Apertium (faster but lower quality):**

```bash
es-translator --interpreter apertium ...
```

**Filter to translate only what's needed:**

```bash
es-translator --query-string "type:Document AND status:published" ...
```

### Memory Issues

Large documents or too many workers can exhaust memory.

**Limit content length:**

```bash
es-translator --max-content-length 10M ...
```

**Reduce worker count:**

```bash
es-translator --pool-size 1 ...
```

**Use Apertium (lower memory usage):**

```bash
es-translator --interpreter apertium ...
```

### High Elasticsearch Load

**Add throttling:**

```bash
es-translator --throttle 100 ...  # 100ms delay
```

**Reduce pool size:**

```bash
es-translator --pool-size 1 ...
```

## Distributed Mode Issues

### Workers Not Processing

**Check Redis connectivity:**

```bash
redis-cli -h redis ping
```

**Verify broker URL matches:**

```bash
# Planning
es-translator --broker-url "redis://redis:6379" --plan ...

# Workers (must use same URL)
es-translator-tasks --broker-url "redis://redis:6379"
```

**Check worker logs:**

```bash
es-translator-tasks --broker-url "redis://..." --stdout-loglevel DEBUG
```

### Tasks Stuck in Queue

**Check Celery status:**

```bash
# If using Docker
docker logs es-translator-worker
```

**Restart workers:**

```bash
docker restart es-translator-worker
```

## Docker Issues

### Container Exits Immediately

Check logs:

```bash
docker logs <container-id>
```

Common causes:

- Missing required arguments (`--source-language`, `--target-language`)
- Invalid Elasticsearch URL
- Network connectivity issues

### Permission Denied

For data directory access:

```bash
docker run -v /path/to/data:/data:rw icij/es-translator \
  es-translator --data-dir /data ...
```

## Debug Mode

Enable detailed logging to diagnose issues:

```bash
es-translator \
  --stdout-loglevel DEBUG \
  --dry-run \
  ...
```

## Dry Run

Test configuration without modifying data:

```bash
es-translator --dry-run ...
```

## Getting Help

If you're still stuck:

1. Check [GitHub Issues](https://github.com/icij/es-translator/issues)
2. Open a new issue with:
    - es-translator version
    - Command you ran
    - Full error message
    - Elasticsearch version
