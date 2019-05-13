DOCKER_NAME := es-translator
VIRTUALENV := venv/

clean:
	find . -name "*.pyc" -exec rm -rf {} \;

install: install_virtualenv install_pip

install_virtualenv:
	# Check if venv folder is already created and create it
	if [ ! -d venv ]; then virtualenv $(VIRTUALENV) --python=python3.5 --no-site-package --distribute; fi

install_pip:
	. $(VIRTUALENV)bin/activate; pip install -r requirements.txt

build-docker:
	docker build -t $(DOCKER_NAME) .

run-docker:
	docker run -it $(DOCKER_NAME) sh
