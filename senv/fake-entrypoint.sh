#!/bin/sh

set -e

if [ -z "$PIP_PACKAGES" ]; then
    echo "The PIP_PACKAGES variable is not set. Something is very wrong"
    exit 1
fi

PYTHON="$(which python)"
mv $PYTHON.real $PYTHON

python -m pip install $PIP_PACKAGES

# Launch the actual command.
# TODO this isn't interruptable when `${0}` is `python`
exec ${0} "${@}"
