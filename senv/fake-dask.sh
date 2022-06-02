#!/bin/sh

set -e

if [ -z "$PIP_PACKAGES" ]; then
    echo "The PIP_PACKAGES variable is not set. Something is very wrong"
    exit 1
fi

python3 -m pip install $PIP_PACKAGES

# This script (`/usr/loca/bin/dask-worker` or `scheduler`) has now been overwritten by the real dask command.
# Launch the actual dask command.

exec ${0} "${@}"
