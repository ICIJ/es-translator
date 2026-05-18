# Zensical Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace MkDocs Material with Zensical (v0.0.42) using its native `zensical.toml` config, keeping the published docs site visually equivalent and dropping Python 3.9.

**Architecture:** Single PR, four atomic commits + one local-validation pass. Sequence chosen so the repo stays buildable at every commit: (1) Python 3.9 drop, (2) atomic Zensical cutover (deps + config + Makefile), (3) CSS port to selector overrides, (4) CI workflow swap. The published GitHub Pages URL is unchanged; the deploy target is unchanged.

**Tech Stack:** Python 3.10+, Poetry, Zensical 0.0.42, mkdocstrings (via Zensical compat shim), TOML config, GitHub Actions, GitHub Pages.

**Reference spec:** `docs/superpowers/specs/2026-05-18-zensical-migration-design.md`

---

## File Structure

| File | Action | Purpose |
|---|---|---|
| `pyproject.toml` | modify | Python floor 3.10, ruff target py310, swap docs deps (drop `mkdocs*`/`cairosvg`, add `zensical`, keep `mkdocstrings*`) |
| `poetry.lock` | regenerate | Reflects new dep set |
| `zensical.toml` | create | Native Zensical config replacing `mkdocs.yml` |
| `mkdocs.yml` | delete | Replaced by `zensical.toml` |
| `docs/stylesheets/extra.css` | modify | Selector-based brand overrides under `default`/`slate` schemes; mermaid keeps variables; typo fixes |
| `Makefile` | modify | `serve-doc` uses `zensical serve`; `publish-doc` becomes a pointer to the release flow |
| `.github/workflows/main.yml` | modify | Drop 3.9 from test matrix; in `publish-docs` job, drop the Cairo step and switch to `zensical build --strict` |
| `docs/*.md` | unchanged | Page content not touched |

---

## Task 1: Drop Python 3.9 support

**Files:**
- Modify: `pyproject.toml:11` (python constraint), `pyproject.toml:55` (ruff target)
- Modify: `.github/workflows/main.yml:15` (matrix)

This is independent of Zensical — it just unblocks installing `zensical` (requires `>=3.10`) in later tasks. After this task the repo is still on MkDocs.

- [ ] **Step 1: Bump Python constraint in `pyproject.toml`**

Change line 11 from:

```toml
python = "^3.9,<3.13"
```

to:

```toml
python = ">=3.10,<3.13"
```

- [ ] **Step 2: Bump ruff target in `pyproject.toml`**

Change line 55 from:

```toml
target-version = "py39"
```

to:

```toml
target-version = "py310"
```

- [ ] **Step 3: Drop 3.9 from the CI matrix**

In `.github/workflows/main.yml` line 15, change:

```yaml
        python-version: ['3.9', '3.10', '3.11', '3.12']
```

to:

```yaml
        python-version: ['3.10', '3.11', '3.12']
```

- [ ] **Step 4: Regenerate `poetry.lock` and install**

Run: `poetry lock --no-update && poetry install`
Expected: exit 0; `poetry.lock` may show small Python-marker changes.

If your local Python is 3.9 and Poetry refuses to install, install Python 3.10+ before continuing (e.g. `pyenv install 3.12 && poetry env use 3.12`).

- [ ] **Step 5: Apply any pyupgrade rewrites enabled by the new target**

Bumping `target-version = "py310"` enables ruff `UP*` rules that may now flag `Union[X, Y]` / `Optional[X]` / `List[X]` / `Dict[X, Y]` as outdated syntax. Auto-fix them in the same commit so CI doesn't fail later.

Run: `make format`
Expected: exit 0. Any modified source files in `es_translator/` and `tests/` are part of this commit.

Inspect the diff: `git diff es_translator tests` — confirm only stylistic / pyupgrade rewrites, no logic changes. If the diff includes anything unexpected, stop and investigate before committing.

- [ ] **Step 6: Verify lint passes**

Run: `make lint`
Expected: exit 0, "Lint OK".

If lint still fails after `make format`, the remaining violations need manual fixing. They may be UP rules that don't auto-fix (rare), in which case fix them by hand or add a targeted `ignore` in `[tool.ruff.lint]`.

- [ ] **Step 7: Verify tests pass**

Run: `make test`
Expected: full suite passes.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml poetry.lock .github/workflows/main.yml es_translator tests
git commit -m "build: drop Python 3.9 support"
```

---

## Task 2: Atomic Zensical cutover

**Files:**
- Modify: `pyproject.toml:28-42` (`[tool.poetry.group.dev.dependencies]`)
- Create: `zensical.toml` (repo root)
- Delete: `mkdocs.yml` (repo root)
- Modify: `Makefile:112-116` (`serve-doc`, `publish-doc` targets)

This task replaces the docs build system in a single commit. The repo's docs build path is unambiguous before and after: MkDocs before, Zensical after. CSS still uses the old `icij-light`/`icij-dark` selectors at the end of this task (Task 3 fixes that) — the site will build but the brand colors won't apply yet.

- [ ] **Step 1: Swap docs dependencies in `pyproject.toml`**

Replace the `[tool.poetry.group.dev.dependencies]` block (currently lines 28-42) with:

```toml
[tool.poetry.group.dev.dependencies]
pyyaml = "*"
argh = "*"
pytest = "^7.2"
pytest-mock = "^3.11.1"
mkdocstrings-python = "^1.12"
mkdocstrings = "^0.27"
zensical = "^0.0.42"
ruff = "^0.14.6"
```

Removed: `mkdocs`, `mkdocs-material`, `mkdocs-exclude`, `mkdocs-minify-plugin`, `mkdocs-autolinks-plugin`, `cairosvg`. Kept: `mkdocstrings`, `mkdocstrings-python` (consumed directly by `zensical.compat.mkdocstrings`).

- [ ] **Step 2: Lock and install**

Run: `poetry lock --no-update && poetry install --no-interaction`
Expected: exit 0; `zensical` resolves; `mkdocs` and friends are removed.

If resolution fails because `zensical` is not yet on PyPI for your Python version, re-check `python` requirement in `pyproject.toml` (must be `>=3.10,<3.13`). If it still fails, pin `zensical = "0.0.42"` (exact) instead of caret.

- [ ] **Step 3: Create `zensical.toml` at repo root**

Write the following content to `zensical.toml`:

```toml
# ============================================================================
# Zensical configuration for es-translator documentation
# Docs: https://zensical.org/docs/
# ============================================================================

[project]
site_name = "EsTranslator"
site_description = "A lazy yet bulletproof machine translation tool for Elasticsearch."
site_url = "https://icij.github.io/es-translator/"
repo_name = "icij/es-translator"
repo_url = "https://github.com/icij/es-translator"
copyright = "Copyright &copy; International Consortium of Investigative Journalists"
extra_css = ["stylesheets/extra.css"]

nav = [
  { "Getting Started" = "index.md" },
  { "Usage" = "usage.md" },
  { "Configuration" = "configuration.md" },
  { "Datashare" = "datashare.md" },
  { "Troubleshooting" = "troubleshooting.md" },
  { "Architecture" = "architecture.md" },
  { "API Reference" = "api.md" },
  { "Contributing" = "contributing.md" },
  { "Releasing" = "releasing.md" },
]

# ----------------------------------------------------------------------------
# Theme
# ----------------------------------------------------------------------------

[project.theme]
variant = "classic"
font.text = "Poppins"
font.code = "Noto Sans Mono"

[project.theme.icon]
logo = "material/translate-variant"

features = [
  "announce.dismiss",
  "content.code.copy",
  "content.tabs.link",
  "navigation.footer",
  "navigation.top",
  "search.highlight",
  "search.share",
  "search.suggest",
  "toc.follow",
]

# Light scheme — ICIJ palette overrides live in docs/stylesheets/extra.css
[[project.theme.palette]]
scheme = "default"
toggle.icon = "lucide/moon"
toggle.name = "Switch to dark theme"

# Dark scheme
[[project.theme.palette]]
scheme = "slate"
toggle.icon = "lucide/sun"
toggle.name = "Switch to light theme"

# ----------------------------------------------------------------------------
# Extras
# ----------------------------------------------------------------------------

[[project.extra.social]]
icon = "fontawesome/brands/github"
link = "https://github.com/ICIJ/es-translator"

[[project.extra.social]]
icon = "fontawesome/brands/python"
link = "https://pypi.org/project/es-translator/"

[[project.extra.social]]
icon = "fontawesome/brands/twitter"
link = "https://twitter.com/ICIJorg"

# ----------------------------------------------------------------------------
# Plugins (kept in MkDocs format — Zensical's compat shim consumes them)
# ----------------------------------------------------------------------------

[project.plugins.search]

[project.plugins.mkdocstrings.config]

[project.plugins.mkdocstrings.config.handlers.python]
paths = ["."]

[project.plugins.mkdocstrings.config.handlers.python.options]
separate_signature = true
filters = ["!^_"]
merge_init_into_class = true

[project.plugins.mkdocstrings.config.handlers.python.options.docstring_options]
ignore_init_summary = true

# ----------------------------------------------------------------------------
# Markdown extensions
# ----------------------------------------------------------------------------

[project.markdown_extensions.tables]
[project.markdown_extensions.admonition]

[project.markdown_extensions.toc]
permalink = true
title = "Page contents"

[project.markdown_extensions.codehilite]
guess_lang = false

[project.markdown_extensions.pymdownx.details]
[project.markdown_extensions.pymdownx.highlight]
[project.markdown_extensions.pymdownx.extra]

[project.markdown_extensions.pymdownx.superfences]
custom_fences = [
  { name = "mermaid", class = "mermaid", format = "pymdownx.superfences.fence_code_format" },
]

[project.markdown_extensions.pymdownx.emoji]
emoji_index = "zensical.extensions.emoji.twemoji"
emoji_generator = "zensical.extensions.emoji.to_svg"

[project.markdown_extensions.pymdownx.tabbed]
alternate_style = true
```

- [ ] **Step 4: Delete `mkdocs.yml`**

Run: `rm mkdocs.yml`

- [ ] **Step 5: Update Makefile docs targets**

In `Makefile`, replace lines 112-116:

```make
serve-doc:
	@poetry run mkdocs serve

publish-doc:
	@poetry run mkdocs gh-deploy
```

with:

```make
serve-doc:
	@poetry run zensical serve --dev-addr 0.0.0.0:4000

publish-doc:
	@echo "Docs are published by CI on release. See docs/releasing.md or run: make bump-patch"
```

- [ ] **Step 6: Build the site to verify**

Run: `poetry run zensical build --strict`
Expected: exit 0, `site/` directory generated, no warnings.

If the build fails with an error about `pymdownx.emoji`, the `emoji_index`/`emoji_generator` paths may be wrong — re-check they point to `zensical.extensions.emoji.twemoji` and `zensical.extensions.emoji.to_svg` (not `material.extensions.emoji.*`).

If it fails with a config-parse error, check TOML syntax — particularly inline tables in `nav` and `extra.social`.

- [ ] **Step 7: Verify the site looks reasonable**

Run: `ls site/` and confirm an `index.html` plus subdirectories for each nav page exist. Open `site/index.html` in a browser or do `poetry run zensical serve --dev-addr 0.0.0.0:4000` and visit `http://localhost:4000`. Don't worry about brand colors yet — that's Task 3.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml poetry.lock zensical.toml Makefile
git rm mkdocs.yml
git commit -m "docs: migrate from MkDocs Material to Zensical"
```

---

## Task 3: Rewrite `extra.css` to selector overrides

**Files:**
- Modify: `docs/stylesheets/extra.css` (full rewrite)

After this task the ICIJ brand (black header, red `#ff0000` accent, dark backgrounds in slate) is intact under both `default` and `slate` schemes. `--md-*` palette variables are removed; mermaid variables stay (the mermaid runtime reads them via its own variable layer). Typos (`#fffff` → `#ffffff`) fixed.

- [ ] **Step 1: Replace `docs/stylesheets/extra.css` with the new content**

Replace the entire file with:

```css
/* ----------------------------------------------------------------------------
 * ICIJ brand palette for Zensical (default + slate schemes)
 *
 * Selector-based overrides instead of --md-* variables, to insulate the brand
 * from any divergence in Zensical's variable system. Mermaid variables stay
 * (they're consumed by the mermaid runtime, not by theme rules).
 * ---------------------------------------------------------------------------- */

/* ---- Light scheme ("default") ---- */

[data-md-color-scheme="default"] {
  color-scheme: light;
}

[data-md-color-scheme="default"] .md-header,
[data-md-color-scheme="default"] .md-tabs {
  background-color: #000;
}

[data-md-color-scheme="default"] .md-typeset {
  color: #3c3c3c;
}

[data-md-color-scheme="default"] .md-typeset a,
[data-md-color-scheme="default"] .md-nav__link--active {
  color: #ff0000;
}

[data-md-color-scheme="default"] .md-nav__title,
[data-md-color-scheme="default"] .md-footer-meta {
  color: #999;
}

[data-md-color-scheme="default"] .md-typeset hr {
  border-color: #00000025;
}

[data-md-color-scheme="default"] .md-typeset table:not([class]),
[data-md-color-scheme="default"] .md-typeset table:not([class]) th,
[data-md-color-scheme="default"] .md-typeset table:not([class]) td {
  border-color: #00000025;
}

/* ---- Dark scheme ("slate") ---- */

[data-md-color-scheme="slate"] {
  color-scheme: dark;
}

body[data-md-color-scheme="slate"] {
  background-color: #1c1c1c;
}

[data-md-color-scheme="slate"] .md-header {
  background-color: #000;
}

[data-md-color-scheme="slate"] .md-tabs {
  background-color: #1c1c1c;
}

[data-md-color-scheme="slate"] .md-typeset,
[data-md-color-scheme="slate"] .md-nav__link {
  color: #ffffff;
}

[data-md-color-scheme="slate"] .md-typeset a,
[data-md-color-scheme="slate"] .md-nav__link--active {
  color: #ff0000;
}

[data-md-color-scheme="slate"] .md-nav__title,
[data-md-color-scheme="slate"] .md-footer-meta {
  color: #e9e9e9;
}

[data-md-color-scheme="slate"] .md-typeset hr {
  border-color: #ffffff25;
}

[data-md-color-scheme="slate"] .md-typeset table:not([class]),
[data-md-color-scheme="slate"] .md-typeset table:not([class]) th,
[data-md-color-scheme="slate"] .md-typeset table:not([class]) td {
  border-color: #ffffff25;
}

[data-md-color-scheme="slate"] .md-typeset code,
[data-md-color-scheme="slate"] .md-typeset pre > code,
[data-md-color-scheme="slate"] .highlight pre {
  background-color: #000;
  color: #ffffff;
}

[data-md-color-scheme="slate"] .highlight .c,
[data-md-color-scheme="slate"] .highlight .c1,
[data-md-color-scheme="slate"] .highlight .cm {
  color: #3c3c3c;
}

[data-md-color-scheme="slate"] .highlight .n,
[data-md-color-scheme="slate"] .highlight .o,
[data-md-color-scheme="slate"] .highlight .p {
  color: #ffffff;
}

[data-md-color-scheme="slate"] .md-typeset .admonition,
[data-md-color-scheme="slate"] .md-typeset details {
  background-color: #3c3c3c;
  color: #ffffff;
}

/* ---- Search input (both schemes) ---- */

[data-md-color-scheme="default"] .md-search__input:not(:focus),
[data-md-color-scheme="slate"] .md-search__input:not(:focus) {
  background: #222;
}

/* ---- Mermaid theming (variables — read by mermaid runtime) ---- */

[data-md-color-scheme="default"] {
  --md-mermaid-node-bg-color: #f5f5f5;
  --md-mermaid-node-fg-color: #3c3c3c;
  --md-mermaid-edge-color: #999;
  --md-mermaid-label-bg-color: #ffffff;
  --md-mermaid-label-fg-color: #3c3c3c;
}

[data-md-color-scheme="slate"] {
  --md-mermaid-node-bg-color: #2a2a2a;
  --md-mermaid-node-fg-color: #e9e9e9;
  --md-mermaid-edge-color: #999;
  --md-mermaid-label-bg-color: #1c1c1c;
  --md-mermaid-label-fg-color: #e9e9e9;
}
```

- [ ] **Step 2: Build the site again**

Run: `poetry run zensical build --strict`
Expected: exit 0, no warnings.

- [ ] **Step 3: Serve and eyeball both schemes**

Run: `poetry run zensical serve --dev-addr 0.0.0.0:4000` and open `http://localhost:4000`.

In both schemes (toggle via the moon/sun button in the header), confirm:
- Header is black.
- Body links and the active nav item are red (`#ff0000`).
- In `slate`: body background is dark (`#1c1c1c`), code blocks have black background with white text, admonitions have a dark grey card background.
- On `architecture.md`, mermaid diagrams render with readable contrast in both schemes.
- The API Reference page (`api.md`) renders all four mkdocstrings blocks (`EsTranslator`, `Argos`, `Apertium`, `ApertiumRepository`).
- Cards on `index.md` render the `:material-*:` icons.

If a specific selector doesn't take effect, open browser devtools and inspect the actual class names Zensical emits. If they differ from Material's `.md-*` conventions, adjust the selectors. Re-run `zensical build` and re-eyeball.

If mermaid colors are wrong in `slate` mode, the variables aren't reaching the mermaid runtime — that's a known-risk follow-up, not blocking this PR. Log it in the PR description.

- [ ] **Step 4: Commit**

```bash
git add docs/stylesheets/extra.css
git commit -m "docs(css): port ICIJ palette to selector-based overrides"
```

---

## Task 4: Update CI publish-docs job

**Files:**
- Modify: `.github/workflows/main.yml:166-178` (Cairo install step and Build docs step)

The `publish-docs` job is only triggered on release events (`if: github.event_name == 'release'`) so it doesn't run on this PR's pushes. The change can still be validated by reading the workflow file diff.

- [ ] **Step 1: Drop the Cairo install step**

In `.github/workflows/main.yml`, remove lines 166-167 (the entire `- name: Install Cairo ...` step including its `run:` line):

```yaml
      - name: Install Cairo (required by mkdocs-material social plugin)
        run: sudo apt-get update -qq && sudo apt-get install -y libcairo2

```

- [ ] **Step 2: Switch the build command to Zensical**

In the same file, change line 178 from:

```yaml
        run: poetry run mkdocs build
```

to:

```yaml
        run: poetry run zensical build --strict
```

- [ ] **Step 3: Lint the workflow file**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/main.yml'))"`
Expected: exit 0 (no YAML parse errors).

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/main.yml
git commit -m "ci: build docs with zensical"
```

---

## Task 5: Local validation walkthrough

**Files:** none (validation only — no commit)

This is the final gate before PR. Catches anything the per-task validation missed. If issues come up, fix forward in a new commit on the same branch.

- [ ] **Step 1: Clean install from scratch**

Run: `rm -rf .venv && poetry install --no-interaction`
Expected: exit 0; `zensical`, `mkdocstrings`, `mkdocstrings-python` all installed; no `mkdocs*` or `cairosvg`.

- [ ] **Step 2: Strict build**

Run: `poetry run zensical build --strict`
Expected: exit 0, zero warnings.

- [ ] **Step 3: Serve and exhaustively eyeball**

Run: `poetry run zensical serve --dev-addr 0.0.0.0:4000` and open `http://localhost:4000`.

For each scheme (toggle via the header button):

- [ ] All nine nav pages load: `Getting Started`, `Usage`, `Configuration`, `Datashare`, `Troubleshooting`, `Architecture`, `API Reference`, `Contributing`, `Releasing`.
- [ ] Header background is black; accent links are red (`#ff0000`).
- [ ] Internal links from `index.md`'s card grid work (clicks navigate, no 404).
- [ ] Search box opens, returns results, highlights matches.
- [ ] Code blocks have the copy button and visible syntax highlighting.
- [ ] Admonitions (any `!!! note` etc.) render with the right card background.
- [ ] Tables have visible border colors.
- [ ] Mermaid diagrams on `architecture.md` are readable in both schemes (nodes, edges, labels).
- [ ] `api.md` renders signatures, attributes, and docstrings for all four classes (`EsTranslator`, `Argos`, `Apertium`, `ApertiumRepository`).
- [ ] `:material-*:` icons in `index.md` card titles render.
- [ ] Social icons (GitHub, Python, Twitter) render in the footer.

- [ ] **Step 4: Compare against the previous published site**

Open `https://icij.github.io/es-translator/` in a second tab. Eyeball-diff page-by-page against your local `zensical serve` output. Note any regressions in the PR description (acceptable losses: social card preview images, HTML minification). Any other regression must be fixed before merge.

- [ ] **Step 5: Confirm full test suite still passes**

Run: `make lint && make test`
Expected: exit 0 for both.

- [ ] **Step 6: Inspect final git log**

Run: `git log --oneline origin/main..HEAD`
Expected: four commits in order — `build: drop Python 3.9 support`, `docs: migrate from MkDocs Material to Zensical`, `docs(css): port ICIJ palette to selector-based overrides`, `ci: build docs with zensical`.

- [ ] **Step 7: Push and open PR**

```bash
git push -u origin <branch-name>
gh pr create --title "Migrate docs from MkDocs Material to Zensical" --body-file - <<'EOF'
## Summary
- Replaces MkDocs Material with Zensical v0.0.42 (native `zensical.toml` config).
- Drops Python 3.9 support.
- Ports `extra.css` to selector-based overrides for the ICIJ palette.
- Drops social-card generation (no Zensical equivalent at v0.0.42); preserves Open Graph metadata via the theme.

## Test plan
- [ ] CI test job passes on 3.10/3.11/3.12.
- [ ] Reviewer pulls the branch and runs `make serve-doc`, eyeballs both schemes.
- [ ] On next release, the `publish-docs` job builds and deploys cleanly.

Spec: `docs/superpowers/specs/2026-05-18-zensical-migration-design.md`
EOF
```

---

## Known follow-ups (out of scope)

1. If mermaid colors don't pick up the `--md-mermaid-*` variables under Zensical, add `docs/javascripts/mermaid-config.js` calling `mermaid.initialize({ themeVariables: {...} })` and reference it via `extra_javascript`.
2. Release notes for the Python 3.9 drop, in the next bumped version (1.13.0 or 2.0.0).
3. If/when Zensical ships a `social` plugin, re-enable social card images.
4. Optionally apply Python 3.10+ syntax patterns (`match`, `X | Y` unions) in `es_translator/`.
