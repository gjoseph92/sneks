FROM sneks-test-base
ARG PIP_PACKAGES
ARG PIP_OVERRIDES

# Pre-install the required deps for faster tests

ENV PIP_PACKAGES="${PIP_PACKAGES}"
ENV PIP_OVERRIDES="${PIP_OVERRIDES}"

# Trigger installtion of pip packages as side effect
RUN python