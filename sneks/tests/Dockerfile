ARG PY_VERSION=3.9.1
FROM jabriel/sneks:$PY_VERSION-full
ARG PIP_PACKAGES

# Pre-install the required deps for faster tests

ENV PIP_PACKAGES="${PIP_PACKAGES}"

# Trigger installtion of pip packages as side effect
RUN python