FROM ubuntu:18.04

RUN apt-get update -qq && apt-get install -qq -y lsb-release wget python3 python3-virtualenv

WORKDIR /tmp
ADD https://apertium.projectjj.com/apt/install-release.sh /tmp/install-release.sh
RUN chmod +x ./install-release.sh && ./install-release.sh

RUN apt-get update -qq && apt-get install -qq -y apertium-all-dev

WORKDIR /opt/es-translator
COPY . .
