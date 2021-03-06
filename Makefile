DOCKER_USER := icij
DOCKER_NAME := es-translator
CURRENT_VERSION ?= `pipenv run python setup.py --version`

clean:
		find . -name "*.pyc" -exec rm -rf {} \;
		rm -rf dist *.egg-info __pycache__

install: install_pip

install_pip:
		pipenv install

minor:
		pipenv run bumpversion --commit --tag --current-version ${CURRENT_VERSION} minor setup.py

major:
		pipenv run bumpversion --commit --tag --current-version ${CURRENT_VERSION} major setup.py

patch:
		pipenv run bumpversion --commit --tag --current-version ${CURRENT_VERSION} patch setup.py

distribute: clean
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
