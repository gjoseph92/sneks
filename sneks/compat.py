from __future__ import annotations

from pathlib import Path
from typing import AbstractSet, Any, Callable

import tomli

from sneks.constants import OPTIONAL_PACKAGES, REQUIRED_PACKAGES
from sneks.parse_pdm import current_versions_pdm
from sneks.parse_poetry import current_versions_poetry
from sneks.plugin import DepManagerBase, PdmDepManager, PoetryDepManager


def find_pyproject() -> Path:
    # TODO actually implement this
    return Path("pyproject.toml")


def sniff_tool_type(pyproject: dict[str, Any]) -> str:
    # TODO handle no build system
    backend: str = pyproject["build-system"]["build-backend"]
    return backend.split(".", maxsplit=1)[0]


def get_backend() -> tuple[DepManagerBase, dict[str, str]]:
    "Get the `DepManagerBase` plugin instance, and extra environment variables"
    pyproject_path = find_pyproject()
    with open(pyproject_path, "rb") as f:
        pyproject = f.read()

    # TODO handle bad TOML
    pyproject_data = tomli.loads(pyproject.decode())
    tool = sniff_tool_type(pyproject_data)

    plugin_type: type[DepManagerBase]
    current_versions_from_lockfile: Callable[
        [AbstractSet[str], AbstractSet[str], dict[str, Any], dict[str, Any]],
        tuple[list[str], list[str]],
    ]
    if tool == "poetry":
        plugin_type = PoetryDepManager
        current_versions_from_lockfile = current_versions_poetry
    elif tool == "pdm":
        plugin_type = PdmDepManager
        current_versions_from_lockfile = current_versions_pdm
    else:
        raise ValueError(f"Unsupported build tool {tool}")

    lockfile_path = pyproject_path.parent / plugin_type.LOCKFILE_NAME
    with open(lockfile_path, "rb") as f:
        lockfile = f.read()
    # TODO handle bad TOML
    lockfile_data = tomli.loads(lockfile.decode())

    required_versions, overrides = current_versions_from_lockfile(
        REQUIRED_PACKAGES, OPTIONAL_PACKAGES, lockfile_data, pyproject_data
    )
    environ = {
        "PIP_PACKAGES": " ".join(required_versions),
        "PIP_OVERRIDES": " ".join(overrides),
    }
    return plugin_type(pyproject, lockfile), environ
