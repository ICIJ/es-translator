---
icon: material/tag
---

# Releasing

This guide describes how to release a new version of es-translator. Releases are automated: creating a GitHub release triggers a CI workflow that publishes the package to PyPI and pushes the Docker image to Docker Hub.

Only maintainers with push access to the repository can perform releases.

## How releases work

A release is produced in three steps:

1. **Bump the version locally** with `make bump-{patch,minor,major}`. This updates `pyproject.toml`, creates a commit, and tags it.
2. **Push the commit and tag** to GitHub.
3. **Create a GitHub release** for the tag. This fires the `release: published` event in `.github/workflows/main.yml`, which runs:
    - The full test matrix (`container-test-job`)
    - `publish-pypi` — builds the package with Poetry and uploads it to PyPI via OIDC (no token needed)
    - `publish-docker` — builds `icij/es-translator:<tag>` and `icij/es-translator:latest` and pushes them to Docker Hub
    - `publish-docs` — builds the MkDocs site and deploys it to GitHub Pages

If any of those steps fail, the release is not published. You can re-run the failed job from the GitHub Actions UI once the cause is fixed.

## One-time setup

Before the first automated release works, two things must be configured on the GitHub side.

### PyPI trusted publisher

es-translator uses [PyPI trusted publishing](https://docs.pypi.org/trusted-publishers/) instead of a long-lived API token. Configure it once:

1. Go to [pypi.org/manage/project/es-translator/settings/publishing/](https://pypi.org/manage/project/es-translator/settings/publishing/)
2. Add a new "GitHub" publisher with:
    - Owner: `ICIJ`
    - Repository: `es-translator`
    - Workflow filename: `main.yml`
    - Environment name: *(leave empty)*

The `publish-pypi` job requests an OIDC token (`permissions: id-token: write`) which PyPI exchanges for short-lived upload credentials. No secret needs to be stored in GitHub.

### Docker Hub credentials

Add two repository secrets in **Settings → Secrets and variables → Actions**:

- `DOCKERHUB_USERNAME` — a Docker Hub account with write access to `icij/es-translator`
- `DOCKERHUB_TOKEN` — a Docker Hub [access token](https://hub.docker.com/settings/security) scoped to `icij/es-translator` with **Read, Write, Delete** permissions

### GitHub Pages

The docs site is deployed via GitHub Actions (no `gh-pages` branch). One-time config:

1. Go to **Settings → Pages**
2. Under **Build and deployment**, set **Source** to **GitHub Actions**

The `publish-docs` job uploads the built site as a Pages artifact (`actions/upload-pages-artifact`) and deploys it with `actions/deploy-pages` using OIDC, so no token needs to be stored.

## Release process

### 1. Verify tests pass

```bash
make lint
make test
```

### 2. Bump the version

Use the semver target that matches the change:

=== "Patch (bug fixes)"

    ```bash
    # 1.12.2 -> 1.12.3
    make bump-patch
    ```

=== "Minor (new features)"

    ```bash
    # 1.12.2 -> 1.13.0
    make bump-minor
    ```

=== "Major (breaking changes)"

    ```bash
    # 1.12.2 -> 2.0.0
    make bump-major
    ```

Each target:

1. Updates the version in `pyproject.toml` via `poetry version`
2. Commits the change as `build: bump to <version> [skip ci]` (the marker skips the redundant push-triggered CI run; the release-triggered publish jobs are unaffected)
3. Tags the commit with `<version>` (no `v` prefix)

The Makefile prints the next steps on success.

### 3. Push the commit and tag

```bash
git push --follow-tags
```

### 4. Create the GitHub release

```bash
gh release create <version> --generate-notes
```

Or open `https://github.com/ICIJ/es-translator/releases/new?tag=<version>` and click **Publish release**.

As soon as the release is published, the workflow runs. Watch it at:

```bash
gh run watch
```

The PyPI package, Docker image, and docs site are all updated automatically when the workflow finishes.

## Version numbering

es-translator follows [Semantic Versioning](https://semver.org/):

| Change type                          | Version bump | Example         |
|--------------------------------------|--------------|-----------------|
| Bug fixes                            | PATCH        | 1.12.2 → 1.12.3 |
| New features (backwards compatible)  | MINOR        | 1.12.2 → 1.13.0 |
| Breaking changes                     | MAJOR        | 1.12.2 → 2.0.0  |

## Makefile reference

| Target                          | Description                                  |
|---------------------------------|----------------------------------------------|
| `make bump-patch`               | Bump patch version (x.x.X)                   |
| `make bump-minor`               | Bump minor version (x.X.0)                   |
| `make bump-major`               | Bump major version (X.0.0)                   |
| `make build`                    | Build sdist and wheel into `dist/`           |
| `make distribute`               | Build and publish to PyPI (manual fallback)  |
| `make docker-setup-multiarch`   | Configure buildx for multi-arch builds       |
| `make docker-publish`           | Build and push Docker image (manual fallback)|
| `make publish-doc`              | Deploy docs to GitHub Pages (manual fallback, uses `gh-pages` branch) |

## Manual fallback

If the automated workflow is unavailable, you can publish from your machine.

### Publish to PyPI manually

```bash
poetry config pypi-token.pypi <your-token>
make distribute
```

### Publish the Docker image manually

```bash
# First-time setup for multi-arch builds
make docker-setup-multiarch

# Login and push
docker login
make docker-publish
```

`make docker-publish` reads the current version from `poetry version -s` and pushes both `icij/es-translator:<version>` and `icij/es-translator:latest`.

### Publish the docs manually

```bash
make publish-doc
```

This runs `mkdocs gh-deploy`, which builds the site and force-pushes it to the `gh-pages` branch. Note that this is the **old** delivery path — if Pages is configured to deploy via Actions, pushing to `gh-pages` will not update the live site. Switch Pages back to "Deploy from a branch" temporarily if you need to use this fallback.

## Troubleshooting

### `publish-pypi` fails with `invalid-publisher`

PyPI cannot find a trusted publisher matching this workflow. Check the publisher entry on PyPI:

- Repository owner is `ICIJ` (case sensitive)
- Workflow filename matches exactly (`main.yml`)
- Environment name is empty (the workflow does not set one)

### `publish-docker` fails at the login step

The Docker Hub secrets are missing, expired, or scoped to the wrong repository. Regenerate the token and update `DOCKERHUB_TOKEN` in the repo settings.

### Tag was created but I don't want to release it

```bash
git tag -d <version>                # delete locally
git push --delete origin <version>  # delete on GitHub
```

Then revert the version-bump commit (`git revert <sha>`) and push.

### Re-running a failed publish

If only one of the publish jobs failed, open the failed run in the GitHub Actions UI and click **Re-run failed jobs**. The publish jobs are idempotent for the Docker image (overwrites the tag) but **not** for PyPI — PyPI rejects re-uploads of the same version. If the PyPI step partially succeeded, you must bump to a new version.
