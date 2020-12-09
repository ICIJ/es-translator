DOCKER_USER := icij
DOCKER_NAME := es-translator
CURRENT_VERSION ?= `python -c "from _version import __version__ ; print(__version__)"`

clean:
		find . -name "*.pyc" -exec rm -rf {} \;

install: install_pip

install_pip:
		pipenv install

minor:
		pipenv run bumpversion --commit --tag --current-version ${CURRENT_VERSION} minor _version.py

major:
		pipenv run bumpversion --commit --tag --current-version ${CURRENT_VERSION} major _version.py

patch:
		pipenv run bumpversion --commit --tag --current-version ${CURRENT_VERSION} patch _version.py

distribute:
		pipenv run python setup.py sdist bdist_wheel
		pipenv run twine upload dist/*

docker-publish: docker-build docker-tag docker-push

docker-run:
		docker run -it $(DOCKER_NAME)

docker-build:
		docker build -t $(DOCKER_NAME) .

docker-tag:
		docker tag $(DOCKER_NAME) $(DOCKER_USER)/$(DOCKER_NAME):${CURRENT_VERSION}

docker-push:
		docker push $(DOCKER_USER)/$(DOCKER_NAME):${CURRENT_VERSION}
