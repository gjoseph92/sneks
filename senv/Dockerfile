ARG IMAGE
FROM $IMAGE

# Create a virtualenv for dask and user code to run in.
# Poetry and especially PDM are much happier to work inside a venv,
# it's fiddly to get them to install into system Python.

ENV VIRTUAL_ENV=/root/.local/sneks-venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH "$VIRTUAL_ENV/bin:$PATH"
# Update pip; might have installation bugs with Poetry otherwise
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install --upgrade wheel

# Install Poetry and PDM in separate, isolated venvs (just like their installers do)
ENV POETRY_HOME=/opt/poetry
ENV PDM_HOME=/opt/pdm
ENV PATH "/root/.local/bin:$PATH"

RUN python3 -m venv $POETRY_HOME &&\
    $POETRY_HOME/bin/pip install --upgrade pip wheel &&\
    $POETRY_HOME/bin/pip install poetry &&\
    $POETRY_HOME/bin/poetry --version
RUN mkdir -p ~/.local/bin &&\
    ln -s $POETRY_HOME/bin/poetry ~/.local/bin/poetry

RUN python3 -m venv $PDM_HOME &&\
    $PDM_HOME/bin/pip install --upgrade pip wheel &&\
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
