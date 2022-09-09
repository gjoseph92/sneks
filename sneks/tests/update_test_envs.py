"""
Run this script any time the main environment is updated.

This keeps the fixture lockfiles used in tests up to date, so their distributed, cloudpickle, etc.
versions match what will be running on the client. Otherwise, adding the DepManager plugin using
that lockfile might install incompatible older versions onto the workers, causing errors when they
restart.
"""

import importlib.metadata
import subprocess
from pathlib import Path

from rich import print

from sneks.constants import REQUIRED_PACKAGES


def update_poetry_env(env: Path, versions: list[str]) -> None:
    if not (env / "pyproject.toml").exists():
        subprocess.run(["poetry", "init", "-n"], shell=False, check=True, cwd=env)
    subprocess.run(
        ["poetry", "add", "--lock"] + versions, shell=False, check=True, cwd=env
    )


def update_test_envs():
    tests = Path(__file__).parent
    versions = [
        f"{pkg}=={importlib.metadata.version(pkg)}"
        for pkg in REQUIRED_PACKAGES
        + ["numpy", "black"]  # `black` used in tests to verify installation happened
    ]
    print(f"Using {versions}")
    update_poetry_env(tests / "env-for-running-poetry", versions)


if __name__ == "__main__":
    update_test_envs()
