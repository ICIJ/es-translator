# Releasing

This guide describes how to release a new version of es-translator. Only maintainers with publish access can perform releases.

## Prerequisites

Before releasing, ensure you have:

- Push access to the GitHub repository
- PyPI credentials configured: `poetry config pypi-token.pypi <your-token>`
- Docker Hub credentials (for Docker image publishing)

## Release Checklist

- [ ] All tests pass (`make test`)
- [ ] Linting passes (`make lint`)
- [ ] Documentation is up to date
- [ ] CHANGELOG updated (if maintained)

## Release Process

### 1. Verify Tests Pass

```bash
make lint
make test
```

### 2. Bump Version

Use semantic versioning targets:

=== "Patch (bug fixes)"

    ```bash
    # 1.0.0 -> 1.0.1
    make patch
    ```

=== "Minor (new features)"

    ```bash
    # 1.0.0 -> 1.1.0
    make minor
    ```

=== "Major (breaking changes)"

    ```bash
    # 1.0.0 -> 2.0.0
    make major
    ```

This will:

1. Update version in `pyproject.toml`
2. Create a commit: `build: bump to <version>`
3. Create a git tag with the version

To set a specific version:

```bash
make set-version CURRENT_VERSION=1.2.3
```

### 3. Push to GitHub

```bash
git push origin master
git push origin --tags
```

### 4. Publish to PyPI

```bash
make distribute
```

This builds and uploads the package to PyPI.

### 5. Publish Docker Image

```bash
# First-time setup for multi-arch builds
make docker-setup-multiarch

# Build and push
make docker-publish
```

This builds and pushes images with both version tag and `latest`.

### 6. Update Documentation

```bash
make publish-doc
```

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):

| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| Bug fixes | PATCH | 1.0.0 → 1.0.1 |
| New features (backward compatible) | MINOR | 1.0.0 → 1.1.0 |
| Breaking changes | MAJOR | 1.0.0 → 2.0.0 |

## Makefile Reference

| Target | Description |
|--------|-------------|
| `make patch` | Bump patch version (x.x.X) |
| `make minor` | Bump minor version (x.X.0) |
| `make major` | Bump major version (X.0.0) |
| `make set-version CURRENT_VERSION=x.x.x` | Set specific version |
| `make distribute` | Build and publish to PyPI |
| `make docker-publish` | Build and push Docker image |
| `make docker-setup-multiarch` | Setup multi-arch Docker builds |
| `make publish-doc` | Deploy docs to GitHub Pages |

## Troubleshooting

### PyPI Upload Fails

Ensure your token is configured:

```bash
poetry config pypi-token.pypi <your-token>
```

### Docker Push Fails

Login to Docker Hub:

```bash
docker login
```

### Multi-arch Build Fails

Setup buildx:

```bash
make docker-setup-multiarch
```
