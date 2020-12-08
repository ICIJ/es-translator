FROM ubuntu:20.04

ENV TZ=US
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt update -qq && apt install -qq -y lsb-release wget python3 \
  pipenv dpkg-dev fakeroot lintian

WORKDIR /tmp
ADD https://apertium.projectjj.com/apt/install-nightly.sh /tmp/install-nightly.sh
RUN chmod +x ./install-nightly.sh && ./install-nightly.sh

RUN apt update -qq && apt install -f -qq -y apertium-all-dev

# Python 3 surrogate unicode handling
# @see https://click.palletsprojects.com/en/7.x/python3/
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

WORKDIR /opt/es-translator

COPY Pipfile .
COPY Pipfile.lock .
RUN pipenv install

COPY . .

CMD ["pipenv", "run", "python", "es_translator.py", "--help"]
