from __future__ import annotations

from typing import AbstractSet, Any


def current_versions_pdm(
    required: AbstractSet[str],
    optional: AbstractSet[str],
    lockfile: dict[str, Any],
    pyproject: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """
    Determine what versions of required and optional packages are installed by parsing the lockfile

    Returns arguments to ``pip install`` to install those packages.

    Also validates that all dependencies in the lockfile will be installable on the cluster (no path deps, for example).
    """
    overrides: dict[str, str]
    try:
        overrides = pyproject["tool"]["pdm"]["overrides"]
    except KeyError:
        overrides = {}

    missing = set(required)
    pip_args: list[str] = []
    pip_overrides: list[str] = []
    for pkg in lockfile["package"]:
        name = pkg["name"]

        try:
            missing.remove(name)
        except KeyError:
            is_required = False
        else:
            is_required = True

        is_optional = (not is_required) and name in optional

        # TODO unlike Poetry, PDM doesn't annotate the lockfile with dependencies' categories.
        # So we can't verify that required packages aren't dev or optional deps.

        # Validate that we'll be able to install it, and ge the pip install arg if necessary.

        # But only for required packages, so as to not be too strict.
        if not (is_required or is_optional):
            continue

        if "path" in pkg and is_required:
            raise NotImplementedError(
                f"Required package {name!r} is installed as a path dependency. "
                "Uploading of local code is not supported yet. Please install from "
                "a Git URL, or use a version on PyPi."
            )

        if git_url := pkg.get("git"):
            # TODO what do other sources besides Git look like?
            pip_arg = f"git+{git_url}@{pkg['revision']}"
        else:
            pip_arg = f"{name}=={pkg['version']}"

        (pip_overrides if name in overrides else pip_args).append(pip_arg)

    if missing:
        missing = sorted(missing)
        raise ValueError(
            f"Required packages {missing} are not dependencies of your environment. "
            "These packages must be installed to create a dask cluster. "
            f"Run `pdm add {' '.join(missing)}` to install them."
        )

    assert not any(
        " " in o for o in overrides
    ), f"Overrides will fail; `sh` does not support arrays containing spaces: {overrides}"
    return pip_args, pip_overrides
