from __future__ import annotations

from typing import AbstractSet

import tomli


def current_versions_poetry(
    required: AbstractSet[str], optional: AbstractSet[str], lockfile: bytes
) -> list[str]:
    """
    Determine what versions of required and optional packages are installed by parsing the lockfile

    Returns arguments to ``pip install`` to install those packages.

    Also validates that all dependencies in the lockfile will be installable on the cluster (no path deps, for example).
    """
    lock = tomli.loads(lockfile.decode())

    missing = set(required)
    pip_args: list[str] = []
    for pkg in lock["package"]:
        name = pkg["name"]

        try:
            missing.remove(name)
        except KeyError:
            is_required = False
        else:
            is_required = True

        is_optional = (not is_required) and name in optional

        if pkg.get("category", "") == "dev":
            if is_required:
                raise ValueError(
                    f"Required package {name} is only a dev dependency. "
                    "Dev dependencies will not be installed on the cluster.\n"
                    f"Upgrade this to a full dependency with `poetry add {name}`, or better, manually move it "
                    "from the `tool.poetry.dev-dependencies` section to the `tool.poetry.dependencies` section "
                    "of your `pyproject.toml`)."
                )
            continue

        if pkg.get("optional", False):
            if is_required:
                raise NotImplementedError(
                    f"Required package {name} is only an optional dependency. "
                    "Optional dependencies will not be installed on the cluster. "
                    "Please open an issue, since perhaps they should be.\n"
                    "For now, please make this a non-optional dependency."
                )
            continue

        # Reached here - package will be installed on cluster.
        # Validate that we'll be able to install it, and ge the pip install arg if necessary.

        if source := pkg.get("source"):
            if (stype := source["type"]) != "git":
                if stype == "directory":
                    raise NotImplementedError(
                        f"Package {name!r} is installed as a path dependency. "
                        "Uploading of local code is not supported yet. Please install from "
                        "a Git URL, or use a version on PyPi."
                    )
                raise NotImplementedError(
                    f"Unsupported package source type {source['type']!r} for {name}. "
                    f"Please open an issue.\n{source=}"
                )
            if "subdirectory" in source:
                raise NotImplementedError(
                    "Subdirectory syntax of git repos not supported yet; "
                    "please open an issue."
                )
            # From git
            if is_required or is_optional:
                pip_args.append(f"git+{source['url']}@{source['resolved_reference']}")
        else:
            # From PyPi
            if is_required or is_optional:
                pip_args.append(f"{name}=={pkg['version']}")

    if missing:
        missing = sorted(missing)
        raise ValueError(
            f"Required packages {missing} are not dependencies of your environment. "
            "These packages must be installed to create a dask cluster. "
            f"Run `poetry add {' '.join(missing)}` to install them."
        )

    return pip_args
