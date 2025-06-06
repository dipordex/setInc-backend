FROM python:3.8-slim-buster

ENV TZ=Europe/London \
    DEBIAN_FRONTEND=noninteractive

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
COPY requirements.txt /
RUN apt-get update \
    && apt-get install -yq --no-install-recommends \
        tini \
        python-dev \
        gcc \
        g++ \
        gdal-bin \
        libgdal-dev \
        libpq-dev \
    && pip install -r /requirements.txt \
    && apt-get -y purge gcc \
    && rm -rf /var/lib/apt/lists/*

ENTRYPOINT [ "tini", "--" ]
