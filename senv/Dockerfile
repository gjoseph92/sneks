ARG IMAGE
FROM $IMAGE

RUN export POETRY_HOME=/opt/poetry &&\
    python3 -m venv $POETRY_HOME &&\
    $POETRY_HOME/bin/pip install poetry &&\
    $POETRY_HOME/bin/poetry --version
RUN ln -s ~/.local/bin/poetry $POETRY_HOME/bin/poetry

RUN export PDM_HOME=/opt/pdm &&\
    python3 -m venv $PDM_HOME &&\
    $PDM_HOME/bin/pip install pdm &&\
    $PDM_HOME/bin/pdm --version
RUN ln -s ~/.local/bin/pdm $PDM_HOME/bin/pdm

COPY fake-entrypoint.sh /fake-entrypoint.sh

RUN TARGET="$(which python)" && \
    BIN="$(dirname $TARGET)" && \
    mv "$TARGET" "$TARGET.real" && \
    mv /fake-entrypoint.sh "$TARGET" && \
    ln -s "$TARGET" "$BIN/dask-worker" && \
    ln -s "$TARGET" "$BIN/dask-scheduler"
