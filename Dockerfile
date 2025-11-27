FROM ubuntu:24.04

# Python 3 surrogate unicode handling
# @see https://click.palletsprojects.com/en/7.x/python3/
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV TZ=US

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update -qq && \
    apt-get install -qq -y --no-install-recommends \
    lsb-release python3 python3-pip dpkg-dev fakeroot lintian curl ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV POETRY_VERSION=1.8.0
ENV PATH="${PATH}:/root/.poetry/bin"
ENV PIP_BREAK_SYSTEM_PACKAGES=1
RUN pip install poetry==$POETRY_VERSION

WORKDIR /tmp
ADD https://apertium.projectjj.com/apt/install-nightly.sh /tmp/install-nightly.sh
RUN chmod +x ./install-nightly.sh && ./install-nightly.sh

RUN apt-get update -qq && \
    apt-get install -f -qq -y apertium-dev cg3 apertium-get apertium-lex-tools && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/es-translator

COPY pyproject.toml poetry.lock /opt/es-translator/
RUN poetry config virtualenvs.create false --local
RUN poetry config installer.max-workers 10 --local
RUN poetry install --no-root --no-interaction --no-ansi --no-cache

COPY . .

RUN poetry install --no-interaction --no-ansi
RUN poetry build

CMD ["es-translator", "--help"]
