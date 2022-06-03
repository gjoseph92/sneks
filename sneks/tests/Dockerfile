# Use an image with the basics pre-installed for faster tests

ARG PY_VERSION=3.9.1
FROM python:$PY_VERSION-slim

# Git is kinda heavy, but often necessary to install packages.
# See https://github.com/docker-library/python/issues/391#issuecomment-481762593
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/*


RUN python3 -c "from urllib.request import urlopen; exec(urlopen('https://install.python-poetry.org').read())"

RUN pip install distributed bokeh
