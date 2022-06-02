# Use an image with the basics pre-installed for faster tests

ARG PY_VERSION=3.9.1
FROM python:$PY_VERSION-slim

RUN python3 -c "from urllib.request import urlopen; exec(urlopen('https://install.python-poetry.org').read())"

RUN pip install distributed bokeh
