ARG IMAGE
FROM $IMAGE

RUN python3 -m pip install --upgrade pip

ENV PATH "/root/.local/bin:$PATH"
ENV POETRY_HOME=/opt/poetry
ENV PDM_HOME=/opt/pdm

RUN python3 -m venv $POETRY_HOME &&\
    $POETRY_HOME/bin/pip install poetry &&\
    $POETRY_HOME/bin/poetry --version
RUN mkdir -p ~/.local/bin &&\
    ln -s $POETRY_HOME/bin/poetry ~/.local/bin/poetry

RUN python3 -m venv $PDM_HOME &&\
    $PDM_HOME/bin/pip install pdm &&\
    $PDM_HOME/bin/pdm --version
RUN mkdir -p ~/.local/bin &&\
    ln -s $PDM_HOME/bin/pdm ~/.local/bin/pdm

COPY fake-entrypoint.sh /fake-entrypoint.sh

RUN TARGET="$(which python)" && \
    BIN="$(dirname $TARGET)" && \
    mv "$TARGET" "$TARGET.real" && \
    mv /fake-entrypoint.sh "$TARGET" && \
    ln -s "$TARGET" "$BIN/dask" && \
    ln -s "$TARGET" "$BIN/dask-worker" && \
    ln -s "$TARGET" "$BIN/dask-scheduler"
