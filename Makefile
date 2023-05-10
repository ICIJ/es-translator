DOCKER_USER := icij
DOCKER_NAME := es-translator
CURRENT_VERSION ?= `poetry version -s`
SEMVERS := major minor patch

clean:
		find . -name "*.pyc" -exec rm -rf {} \;
		rm -rf dist *.egg-info __pycache__

install: poetry_install

poetry_install:
		poetry install

test:
		poetry run pytest

tag_version: 
		git commit -m "build: bump to ${CURRENT_VERSION}" pyproject.toml
		git tag ${CURRENT_VERSION}

set_version:
		poetry version ${CURRENT_VERSION}
		$(MAKE) tag_version

$(SEMVERS):
		poetry version $@
		$(MAKE) tag_version

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