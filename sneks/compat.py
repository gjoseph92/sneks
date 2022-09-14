from __future__ import annotations

from pathlib import Path
from typing import Callable

import tomli

from sneks.constants import REQUIRED_PACKAGES
from sneks.parse_pdm import current_versions_pdm
from sneks.parse_poetry import current_versions_poetry
from sneks.plugin import DepManagerBase, PdmDepManager, PoetryDepManager


def find_pyproject() -> Path:
    # TODO actually implement this
    return Path("pyproject.toml")


def sniff_tool_type(pyproject: bytes) -> str:
    # TODO handle bad TOML
    pyproject_data = tomli.loads(pyproject.decode())

    # TODO handle no build system
    backend: str = pyproject_data["build-system"]["build-backend"]
    return backend.split(".", maxsplit=1)[0]


def get_backend() -> tuple[DepManagerBase, dict[str, str]]:
    "Get the `DepManagerBase` plugin instance, and extra environment variables"
    pyproject_path = find_pyproject()
    with open(pyproject_path, "rb") as f:
        pyproject = f.read()

    tool = sniff_tool_type(pyproject)
    plugin_type: type[DepManagerBase]
    current_versions_from_lockfile: Callable[[list[str], bytes], list[str]]
    if tool == "poetry":
        plugin_type = PoetryDepManager
        current_versions_from_lockfile = current_versions_poetry
    elif tool == "sneks":
        plugin_type = PdmDepManager
        current_versions_from_lockfile = current_versions_pdm
    else:
        raise ValueError(f"Unsupported build tool {tool}")

    lockfile_path = pyproject_path.parent / plugin_type.LOCKFILE_NAME
    with open(lockfile_path, "rb") as f:
        lockfile = f.read()

    required_versions = current_versions_from_lockfile(REQUIRED_PACKAGES, lockfile)
    environ = {"PIP_PACKAGES": " ".join(required_versions)}
    return plugin_type(pyproject, lockfile), environ
