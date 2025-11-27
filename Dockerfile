FROM ubuntu:24.04

# Python 3 surrogate unicode handling
# @see https://click.palletsprojects.com/en/7.x/python3/
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV TZ=US

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt update -qq && apt install -qq -y lsb-release \
  python3 python3-pip dpkg-dev fakeroot lintian

ENV POETRY_VERSION=1.3.1
ENV PATH="${PATH}:/root/.poetry/bin"
RUN pip install poetry==$POETRY_VERSION

WORKDIR /tmp
ADD https://apertium.projectjj.com/apt/install-nightly.sh /tmp/install-nightly.sh
RUN chmod +x ./install-nightly.sh && ./install-nightly.sh

RUN apt update -qq && apt install -f -qq -y apertium-dev \
  cg3 apertium-get apertium-lex-tools

WORKDIR /opt/es-translator

COPY pyproject.toml poetry.lock /opt/es-translator/
RUN poetry config virtualenvs.create false --local
RUN poetry install --no-root --no-interaction --no-ansi

COPY . .

RUN poetry install --no-interaction --no-ansi
RUN poetry build

CMD ["es-translator", "--help"]
