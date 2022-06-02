ARG PY_VERSION
FROM python:$PY_VERSION-slim

RUN python3 -c "from urllib.request import urlopen; exec(urlopen('https://install.python-poetry.org').read())"

RUN mv /usr/local/bin/python /usr/local/bin/python.real

COPY fake-entrypoint.sh /usr/local/bin/python
COPY fake-entrypoint.sh /usr/local/bin/dask-worker
COPY fake-entrypoint.sh /usr/local/bin/dask-scheduler