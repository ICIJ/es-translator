# Migrate es-translator docs from MkDocs Material to Zensical

**Date:** 2026-05-18
**Status:** Design — pending review

## Goal

Replace the MkDocs Material documentation build with Zensical's native config, keeping the published site visually and functionally equivalent. Drive: follow upstream — Zensical is the stated successor to Material for MkDocs, built by the same authors.

## Non-goals

- Changing the documentation content (page bodies, structure, nav order).
- Changing the deploy target (still GitHub Pages at `https://icij.github.io/es-translator/`).
- Refactoring `es_translator/` source code to use Python 3.10+ syntax. The Python floor moves to 3.10, but applying new syntax patterns is a separate task.
- Building any Zensical-specific tooling. We use Zensical as shipped (v0.0.42).

## Target state

| Aspect | Before | After |
|---|---|---|
| Build tool | `mkdocs` + `mkdocs-material` | `zensical` |
| Config file | `mkdocs.yml` (YAML) | `zensical.toml` (TOML) |
| API reference | `mkdocstrings` plugin | `mkdocstrings` via Zensical compat shim |
| Search | `mkdocs-material` search | Zensical native search |
| Cross-refs | `mkdocs-autolinks-plugin` | Zensical native autorefs |
| Social cards | `mkdocs-material` `social` plugin + `libcairo2` | Dropped (no Zensical equivalent at v0.0.42) |
| HTML minify | `mkdocs-minify-plugin` | Dropped |
| Path exclude | `mkdocs-exclude` | Dropped |
| Palette CSS | `--md-*` variable overrides under custom scheme names | Selector-based overrides under `default`/`slate` schemes |
| Python floor | 3.9 | 3.10 |

## Constraints driving the design

- Zensical is at v0.0.42 (Alpha). Breaking changes possible; rollback path must stay simple.
- Zensical requires Python ≥3.10. Project currently supports 3.9. The docs CI job already pins to 3.12, but Poetry dep resolution must work for non-docs envs too — we drop 3.9 entirely rather than carry a compatibility shim.
- The published GitHub Pages URL must not change.

## Approach

Single PR. Convert config from `mkdocs.yml` to `zensical.toml`, swap dependencies, port CSS to selector-based overrides, swap CI build command, drop Python 3.9. No staged rollout — the site is regenerated atomically on the next release.

## Changes

### 1. New file: `zensical.toml`

At repo root. Replaces `mkdocs.yml`. Structure:

- `[project]` — `site_name`, `site_description`, `site_url`, `repo_name`, `repo_url`, `copyright`, `extra_css`, `nav`.
- `[project.theme]` — `variant = "classic"`, `font.text`, `font.code`, `icon.logo`.
- `[[project.theme.palette]]` × 2 — `scheme = "default"` with `lucide/moon` toggle, `scheme = "slate"` with `lucide/sun` toggle.
- `[project.theme.features]` — `announce.dismiss`, `content.code.copy`, `content.tabs.link`, `navigation.footer`, `navigation.top`, `search.highlight`, `search.share`, `search.suggest`, `toc.follow`.
- `[[project.extra.social]]` × 3 — GitHub, PyPI, Twitter.
- `[project.plugins.search]` — defaults.
- `[project.plugins.mkdocstrings.config]` + `handlers.python` — paths `["."]`, `separate_signature = true`, `filters = ["!^_"]`, `merge_init_into_class = true`, `docstring_options.ignore_init_summary = true`.
- `[project.markdown_extensions.*]` — `tables`, `admonition`, `toc` (permalink, title), `codehilite` (guess_lang false), `pymdownx.details`, `pymdownx.highlight`, `pymdownx.extra`, `pymdownx.superfences` (mermaid custom_fence), `pymdownx.emoji` (using `zensical.extensions.emoji.twemoji` + `to_svg`), `pymdownx.tabbed` (alternate_style).

Drop from old config: `social`, `autolinks`, `minify`, `exclude` plugin entries. `dev_addr` moves to a CLI flag.

### 2. Rewrite `docs/stylesheets/extra.css`

Aggressive rewrite — replace every `--md-*` variable assignment with a direct property override on the rendered selector. Mermaid variables (`--md-mermaid-*`) are the only exception: they stay as variables since the mermaid runtime reads them via its own variable-resolution layer.

- Rename `[data-md-color-scheme="icij-light"]` → `[data-md-color-scheme="default"]`.
- Rename `[data-md-color-scheme="icij-dark"]` → `[data-md-color-scheme="slate"]`.
- Map each variable to a selector rule:
  - `--md-primary-fg-color` → `.md-header { background-color: #000; }` and `.md-tabs { background-color: #000; }`.
  - `--md-accent-fg-color`, `--md-typeset-a-color` → `.md-typeset a, .md-nav__link--active { color: #ff0000; }`.
  - `--md-typeset-color` → `.md-typeset { color: ...; }` (light: `#3c3c3c`, dark: `#fff`).
  - `--md-default-bg-color` (dark) → `body[data-md-color-scheme="slate"] { background-color: #1c1c1c; }`.
  - `--md-default-fg-color--light/lightest` → targeted rules on `.md-nav__title`, `.md-footer-meta`, border colors.
  - `--md-typeset-table-color` → `.md-typeset table:not([class]) { border-color: ...; }`.
  - `--md-code-bg-color`, `--md-code-fg-color`, `--md-code-hl-*` → rules on `.md-typeset code`, `.md-typeset pre`, `.highlight .o/.p/.n/.c`.
  - `--md-admonition-fg-color`, `--md-admonition-bg-color` → rules on `.md-typeset .admonition`, `.md-typeset details`.
  - Search-input rule keeps its selector form, only scheme name updated.
- Each new rule scoped with `[data-md-color-scheme="default"]` or `[data-md-color-scheme="slate"]` ancestor so light/dark stay independent.
- Keep `--md-mermaid-node-bg-color`, `--md-mermaid-node-fg-color`, `--md-mermaid-edge-color`, `--md-mermaid-label-bg-color`, `--md-mermaid-label-fg-color` assignments as-is under both schemes.
- Fix typos: `#fffff` → `#ffffff` on lines 30, 33, 35, 36, 37, 43.

If a selector doesn't take effect during validation, bump its specificity or adjust the target. Worst-case fallback for mermaid (if Zensical doesn't honor the variables) is a follow-up `docs/javascripts/mermaid-config.js` calling `mermaid.initialize({ themeVariables: {...} })` — out of scope for this PR; tracked as a known risk.

### 3. Update `pyproject.toml`

- Bump `python = "^3.9,<3.13"` → `python = ">=3.10,<3.13"`.
- Bump `[tool.ruff] target-version = "py39"` → `"py310"`.
- In `[tool.poetry.group.dev.dependencies]`:
  - Remove `mkdocs`, `mkdocs-material`, `mkdocs-exclude`, `mkdocs-minify-plugin`, `mkdocs-autolinks-plugin`, `cairosvg`.
  - Keep `mkdocstrings`, `mkdocstrings-python` (imported directly by `zensical.compat.mkdocstrings`).
  - Add `zensical` (no version pin until a stable release; pin to compatible range once 1.0 lands).
- Regenerate `poetry.lock` with `poetry lock`.

### 4. Update `Makefile`

Two affected targets:

- `serve-doc:` change `poetry run mkdocs serve` → `poetry run zensical serve --dev-addr 0.0.0.0:4000`.
- `publish-doc:` previously ran `mkdocs gh-deploy`. CI now publishes on release (commit `76dddd9`), so the local target is vestigial. Replace its body with an echo pointing to the release flow:
  ```make
  publish-doc:
  	@echo "Docs are published by CI on release. See docs/releasing.md or run: make bump-patch"
  ```
  Keep the target so existing muscle memory doesn't fail silently.

### 5. Update `.github/workflows/main.yml`

- `container-test-job` matrix: drop `'3.9'`. Result: `python-version: ['3.10', '3.11', '3.12']`.
- `publish-docs` job:
  - Remove the `Install Cairo` step.
  - Change `poetry run mkdocs build` → `poetry run zensical build --strict`.
  - Everything else (Poetry install, pages setup, artifact upload, deploy) unchanged.

### 6. Delete `mkdocs.yml`

Final cleanup — removed once `zensical.toml` is in place and verified.

## Files touched

- New: `zensical.toml`
- Deleted: `mkdocs.yml`
- Modified: `docs/stylesheets/extra.css`, `pyproject.toml`, `poetry.lock` (regenerated), `Makefile`, `.github/workflows/main.yml`
- Unchanged: every file under `docs/` except `extra.css` (page content stays as-is)

## Validation

Done locally before pushing; CI re-validates on the PR.

### Local

1. `poetry install` (fresh env after pyproject changes).
2. `poetry run zensical build --strict` — must exit 0 with no warnings.
3. `poetry run zensical serve --dev-addr 0.0.0.0:4000`.
4. Browser checks in both `default` and `slate` schemes:
   - Header is black; accent links are red (`#ff0000`).
   - All nine nav pages load.
   - API page renders all four mkdocstrings blocks (`EsTranslator`, `Argos`, `Apertium`, `ApertiumRepository`) with signatures, attributes, methods, docstrings.
   - Mermaid diagrams in `architecture.md` render with readable colors in both schemes.
   - Code blocks have copy button + correct syntax highlighting.
   - Admonitions, tables, internal links, search, Material-style icons (`:material-*:` in `index.md`) all render.
5. Diff `site/` tree against an MkDocs-built `site/` — confirm no missing pages.

### CI

- Test job passes on 3.10/3.11/3.12.
- `publish-docs` is gated by `if: github.event_name == 'release'` and won't run on the PR. To pre-validate, temporarily add a `workflow_dispatch` trigger on a draft commit, run once, restore the gate before merging.

### Post-merge

- First post-merge release triggers `publish-docs`. Monitor the Action run; if it fails, `git revert` + patch release.

## Known risks

1. **`pymdownx.emoji` namespace** — `material.extensions.emoji.*` must become `zensical.extensions.emoji.*` in `zensical.toml`. The compat layer auto-rewrites in YAML mode but not in TOML mode. Risk: a stray reference somewhere we missed.
2. **Mermaid color variables** — Zensical may not pass `--md-mermaid-*` to the mermaid runtime. Fallback: ship a `mermaid-config.js` initializer in a follow-up.
3. **Selector rewrites missing a case** — visible as a styling regression. Fix forward during the validation pass.
4. **`extra.social` schema inference** — the `[[project.extra.social]]` form is taken from the bootstrap comment example. If icons don't render, adjust schema or drop the section (CTAs are also in the README).
5. **Zensical alpha breakage** — upstream may release a backwards-incompatible v0.0.43 before we merge. Mitigation: pin to v0.0.42 in `pyproject.toml` if the build is brittle.
6. **Python 3.9 drop is a breaking change for downstream `es-translator` users.** Out of migration scope but must be called out in the release notes for the next minor/major bump (1.13.0 or 2.0.0).

## Rollback

Revert the migration commit. The previously-published GitHub Pages site keeps serving until the next release succeeds; no partial-state risk.

## Out of scope (tracked separately)

- Applying Python 3.10+ syntax patterns in `es_translator/` (match, `X | Y` unions, etc.).
- Re-introducing social card images if/when Zensical ships a `social` plugin.
- Migrating to a hypothetical future Zensical config format (this design uses what ships at v0.0.42).
- Version bump and release notes for the Python 3.9 drop.
