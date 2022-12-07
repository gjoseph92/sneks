from __future__ import annotations

from sneks.constants import REQUIRED_PACKAGES
from sneks.tests.update_test_envs import PIP_OVERRIDES

# Set PIP_PACKAGES, PIP_OVERRIDES, and PY_VERSION env vars for docker compose to pick
# up, ensuring versions installed in docker match versions installed locally


def set_pip_packages(required_packages: list[str]):
    import importlib.metadata
    import os

    pip_packages = " ".join(
        [f"{pkg}=={importlib.metadata.version(pkg)}" for pkg in required_packages]
        # `yapf` used in tests to verify it's removed by installation
        + ["yapf"]
    )
    os.environ["PIP_PACKAGES"] = pip_packages
    print(f'PIP_PACKAGES="{pip_packages}"')


def set_pip_overrides():
    import os

    pip_overrides = " ".join(f"{k}=={v}" for k, v in PIP_OVERRIDES.items())
    os.environ["PIP_OVERRIDES"] = pip_overrides
    print(f'PIP_OVERRIDES="{pip_overrides}"')


def set_py_version():
    import os
    import sys

    version = sys.version_info
    py_version = f"{version.major}.{version.minor}.{version.micro}"
    os.environ["PY_VERSION"] = py_version
    print(f'PY_VERSION="{py_version}"')


set_pip_packages(list(REQUIRED_PACKAGES))
set_pip_overrides()
set_py_version()
