from __future__ import annotations

"""
This keeps the fixture lockfiles used in tests up to date, so their distributed, cloudpickle, etc.
versions match what will be running on the client. Otherwise, adding the DepManager plugin using
that lockfile might install incompatible older versions onto the workers, causing errors when they
restart.

This script is run automatically via a the pytest fixture `updated_test_envs`.
"""

import importlib.metadata
import subprocess
from pathlib import Path

from rich import print

from sneks.constants import REQUIRED_PACKAGES


def update_poetry_env(env: Path, versions: list[str]) -> None:
    env.mkdir(exist_ok=True)
    if not (env / "pyproject.toml").exists():
        subprocess.run(["poetry", "init", "-n"], shell=False, check=True, cwd=env)
    subprocess.run(
        # --lock prevents actually installing them; just does lock
        ["poetry", "add", "--lock"] + versions,
        shell=False,
        check=True,
        cwd=env,
    )


def update_pdm_env(env: Path, versions: list[str], overrides: dict[str, str]) -> None:
    env.mkdir(exist_ok=True)
    if not (env / "pyproject.toml").exists():
        subprocess.run(["pdm", "init", "-n"], shell=False, check=True, cwd=env)
    subprocess.run(
        # --no-sync prevents actually installing them; just does lock
        ["pdm", "add", "--no-sync"] + versions,
        shell=False,
        check=True,
        cwd=env,
    )

    with open(env / "pyproject.toml", "a") as f:
        f.write("\n[tool.pdm.overrides]\n")
        for k, v in overrides.items():
            f.write(f'{k} = "{v}"\n')

    subprocess.run(
        ["pdm", "lock"],
        shell=False,
        check=True,
        cwd=env,
    )


def update_test_envs():
    tests = Path(__file__).parent
    versions = [
        f"{pkg}=={importlib.metadata.version(pkg)}"
        for pkg in list(REQUIRED_PACKAGES)
        + ["numpy", "black"]  # `black` used in tests to verify installation happened
    ]
    print(f"Using {versions}")
    print("[bold][white]Setting up Poetry env[/]")
    update_poetry_env(tests / "env-for-running-poetry", versions)
    print("[bold][white]Setting up PDM env[/]")
    update_pdm_env(
        tests / "env-for-running-pdm",
        versions,
        overrides={
            # Override a transitive dependency of `black`:
            # https://github.com/psf/black/blob/d4a85643a465f5fae2113d07d22d021d4af4795a/pyproject.toml#L67
            "mypy_extensions": "0.4.2"
        },
    )


if __name__ == "__main__":
    update_test_envs()
