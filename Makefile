DOCKER_USER := icij
DOCKER_NAME := es-translator
DOCKER_TAG := latest
VIRTUALENV := venv/

clean:
		find . -name "*.pyc" -exec rm -rf {} \;

install: install_virtualenv install_pip

install_virtualenv:
		# Check if venv folder is already created and create it
		if [ ! -d venv ]; then virtualenv $(VIRTUALENV) --python=python3.5 --no-site-package --distribute; fi

install_pip:
		. $(VIRTUALENV)bin/activate; pip install -r requirements.txt

docker-publish: docker-build docker-tag docker-push

docker-run:
		docker run -p 3000:3000 -it $(DOCKER_NAME)

docker-build:
		docker build -t $(DOCKER_NAME) .

docker-tag:
		docker tag $(DOCKER_NAME) $(DOCKER_USER)/$(DOCKER_NAME):$(DOCKER_TAG)

docker-push:
		docker push $(DOCKER_USER)/$(DOCKER_NAME):$(DOCKER_TAG)
