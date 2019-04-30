FROM debian:stretch-slim

WORKDIR /tmp
ADD https://apertium.projectjj.com/apt/install-nightly.sh
RUN chmod +x ./install-nightly.sh && ./install-nightly.sh

RUN apt-get update -qq && apt-get install -qq apertium-all-dev
