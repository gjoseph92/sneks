FROM sneks-test-base
ARG PIP_PACKAGES

# Pre-install the required deps for faster tests

ENV PIP_PACKAGES="${PIP_PACKAGES}"

# Trigger installtion of pip packages as side effect
RUN python