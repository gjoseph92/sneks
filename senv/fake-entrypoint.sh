#!/bin/sh

set -e

if [ -z "$PIP_PACKAGES" ]; then
    echo "The PIP_PACKAGES variable is not set. Something is very wrong"
    exit 1
fi

PYTHON="$(which python)"
mv $PYTHON.real $PYTHON

python -m pip install $PIP_PACKAGES

echo "$PIP_OVERRIDES"

if [ -z "$PIP_OVERRIDES" ]; then
    echo "No pip overrides to install"
else
    echo "Installing overrides: $PIP_OVERRIDES"
    for ARG in ${PIP_OVERRIDES}; do
        python -m pip install "$ARG"
    done
fi

# Launch the actual command.
# TODO this isn't interruptable when `${0}` is `python`
exec ${0} "${@}"
