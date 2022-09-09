ARG IMAGE
FROM $IMAGE

RUN python3 -c "from urllib.request import urlopen; exec(urlopen('https://install.python-poetry.org').read())"
RUN python3 -c "from urllib.request import urlopen; exec(urlopen('https://raw.githubusercontent.com/pdm-project/pdm/main/install-pdm.py').read())"

COPY fake-entrypoint.sh /fake-entrypoint.sh

RUN TARGET="$(which python)" && \
    BIN="$(dirname $TARGET)" && \
    mv "$TARGET" "$TARGET.real" && \
    mv /fake-entrypoint.sh "$TARGET" && \
    ln -s "$TARGET" "$BIN/dask-worker" && \
    ln -s "$TARGET" "$BIN/dask-scheduler"
