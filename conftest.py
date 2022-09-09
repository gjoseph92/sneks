from __future__ import annotations

from sneks.frontend import REQUIRED_PACKAGES

# Set PIP_PACKAGES env var for docker compose to pick up, ensuring versions installed in docker
# match versions installed locally


def set_pip_packages(required_packages: list[str]):
    import importlib.metadata
    import os

    pip_packages = " ".join(
        f"{pkg}=={importlib.metadata.version(pkg)}" for pkg in required_packages
    )
    os.environ["PIP_PACKAGES"] = pip_packages
    print(f'PIP_PACKAGES="{pip_packages}"')


# Include coiled since the bloat makes it very slow to install during tests
set_pip_packages(REQUIRED_PACKAGES + ["coiled", "rich"])
