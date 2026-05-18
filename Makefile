.PHONY: help install test lint format clean build distribute \
        bump-patch bump-minor bump-major _bump _bump-success \
        docker-setup-multiarch docker-publish docker-run \
        serve-doc publish-doc

SRC := es_translator
DOCKER_USER := icij
DOCKER_NAME := es-translator

help:
	@echo "es-translator - Machine translation for Elasticsearch"
	@echo ""
	@echo "Development:"
	@echo "  make install        Install dependencies via poetry"
	@echo "  make test           Run unit tests"
	@echo "  make lint           Check code style"
	@echo "  make format         Auto-format code"
	@echo "  make clean          Remove cache files"
	@echo ""
	@echo "Documentation:"
	@echo "  make serve-doc      Serve the documentation locally"
	@echo "  make publish-doc    Deploy documentation to GitHub Pages"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-setup-multiarch   Configure buildx for multi-arch builds"
	@echo "  make docker-publish           Build and push the Docker image"
	@echo "  make docker-run               Run the Docker image locally"
	@echo ""
	@echo "Release:"
	@echo "  make build          Build sdist and wheel into dist/"
	@echo "  make distribute     Publish the package to PyPI"
	@echo "  make bump-patch     Bump patch version (1.12.2 -> 1.12.3)"
	@echo "  make bump-minor     Bump minor version (1.12.2 -> 1.13.0)"
	@echo "  make bump-major     Bump major version (1.12.2 -> 2.0.0)"

install:
	@poetry install

test:
	@poetry run pytest

lint:
	@poetry run ruff check $(SRC) && poetry run ruff format --check $(SRC) && echo "Lint OK"

format:
	@poetry run ruff check --fix $(SRC) && poetry run ruff format $(SRC) && echo "Format OK"

clean:
	@find . -name "*.pyc" -delete
	@rm -rf dist build *.egg-info
	@rm -rf $(SRC)/__pycache__ tests/__pycache__ __pycache__
	@rm -rf .pytest_cache .ruff_cache .coverage htmlcov
	@echo "Cleaned"

build:
	@rm -rf dist
	@poetry build
	@echo ""
	@echo "Built artifacts:"
	@ls -1 dist

distribute:
	@poetry publish --build

_bump:
	@NEW_VERSION=$$(poetry version -s); \
	git commit -m "build: bump to $$NEW_VERSION" pyproject.toml; \
	git tag $$NEW_VERSION

_bump-success:
	@NEW_TAG=$$(git describe --tags --abbrev=0); \
	echo ""; \
	echo "✓ Version bumped to $$NEW_TAG"; \
	echo ""; \
	echo "Next steps:"; \
	echo "  1. Push the commit and tag:"; \
	echo "       git push --follow-tags"; \
	echo "  2. Create a GitHub release for $$NEW_TAG:"; \
	echo "       gh release create $$NEW_TAG --generate-notes"; \
	echo "     or open: https://github.com/ICIJ/es-translator/releases/new?tag=$$NEW_TAG"

bump-patch:
	@poetry version patch
	@$(MAKE) --no-print-directory _bump
	@$(MAKE) --no-print-directory _bump-success

bump-minor:
	@poetry version minor
	@$(MAKE) --no-print-directory _bump
	@$(MAKE) --no-print-directory _bump-success

bump-major:
	@poetry version major
	@$(MAKE) --no-print-directory _bump
	@$(MAKE) --no-print-directory _bump-success

docker-setup-multiarch:
	@docker run --privileged --rm tonistiigi/binfmt --install all
	@docker buildx create --use

docker-publish:
	@CURRENT_VERSION=$$(poetry version -s); \
	docker buildx build \
		--platform linux/amd64 \
		-t $(DOCKER_USER)/$(DOCKER_NAME):$$CURRENT_VERSION \
		-t $(DOCKER_USER)/$(DOCKER_NAME):latest \
		--push .

docker-run:
	@docker run -it $(DOCKER_NAME)

serve-doc:
	@poetry run mkdocs serve

publish-doc:
	@poetry run mkdocs gh-deploy
