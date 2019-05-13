FROM ubuntu:18.04

RUN apt-get update -qq && apt-get install -qq -y lsb-release wget python3 python3-pip python3-virtualenv

WORKDIR /tmp
ADD https://apertium.projectjj.com/apt/install-release.sh /tmp/install-release.sh
RUN chmod +x ./install-release.sh && ./install-release.sh

RUN apt-get update -qq && apt-get install -qq -y apertium-all-dev

# Configure python to use our virtual env
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m virtualenv --python=/usr/bin/python3 $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Python 3 surrogate unicode handling
# @see https://click.palletsprojects.com/en/7.x/python3/
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

WORKDIR /opt/es-translator

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "es_translator.py", "--help"]
