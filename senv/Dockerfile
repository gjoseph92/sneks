ARG PY_VERSION
FROM python:$PY_VERSION-slim

RUN python3 -c "from urllib.request import urlopen; exec(urlopen('https://install.python-poetry.org').read())"

COPY fake-dask.sh /usr/local/bin/dask-worker
COPY fake-dask.sh /usr/local/bin/dask-scheduler