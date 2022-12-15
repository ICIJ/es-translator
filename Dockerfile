FROM ubuntu:22.04

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

RUN apt update -qq && apt install -f -qq -y apertium-all-dev \
  cg3 apertium-get apertium-lex-tools


WORKDIR /opt/es-translator

COPY . .
RUN poetry install
RUN poetry build

CMD ["poetry", "run", "es-translator", "--help"]
