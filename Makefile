DOCKER_USER := icij
DOCKER_NAME := es-translator
CURRENT_VERSION ?= `git describe --tags --always --abbrev=0 | sed 's/^v//'`
SEMVERS := major minor patch

clean:
		find . -name "*.pyc" -exec rm -rf {} \;
		rm -rf dist *.egg-info __pycache__

install: poetry-install

poetry-install:
		poetry install

test:
		poetry run pytest

tag-version: 
		git commit -m "build: bump to ${CURRENT_VERSION}" pyproject.toml
		git tag ${CURRENT_VERSION}

set-version:
		poetry version ${CURRENT_VERSION}
		$(MAKE) tag-version

$(SEMVERS):
		poetry version $@
		$(MAKE) tag-version

distribute:
		poetry publish --build 

docker-setup-multiarch:
		docker run --privileged --rm tonistiigi/binfmt --install all
		docker buildx create --use

docker-publish:
		docker buildx build \
			--platform linux/amd64 \
			-t $(DOCKER_USER)/$(DOCKER_NAME):${CURRENT_VERSION} \
			-t $(DOCKER_USER)/$(DOCKER_NAME):latest \
			--push .

docker-run:
		docker run -it $(DOCKER_NAME)

publish-doc:
		poetry run mkdocs gh-deploy

serve-doc:
		poetry run mkdocs serve