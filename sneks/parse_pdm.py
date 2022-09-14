from __future__ import annotations

import tomli


def current_versions_pdm(packages: list[str], lockfile: bytes) -> list[str]:
    "Determine what versions of ``packages`` are currently installed by parsing the lockfile"
    lock = tomli.loads(lockfile.decode())
    pset = set(packages)
    matches = {name: p for p in lock["package"] if (name := p["name"]) in pset}
    if missing := sorted(pset - matches.keys()):
        raise ValueError(
            f"Required packages {missing} are not dependencies of your environment. "
            "These packages must be installed to create a dask cluster. "
            f"Run `pdm add {' '.join(missing)}` to install them."
        )

    pip_args: list[str] = []
    for name, p in matches.items():
        # TODO unlike Poetry, PDM doesn't annotate the lockfile with dependencies' categories.
        # So we can't verify that required packages aren't dev or optional deps.
        if "path" in p:
            raise NotImplementedError(
                f"Required package {name!r} is installed as a path dependency. "
                "Uploading of local code is not supported yet. Please install from "
                "a Git URL, or use a version on PyPi."
            )
        if git_url := p.get("git"):
            # TODO what do other sources besides Git look like?
            pip_arg = f"git+{git_url}@{p['revision']}"
        else:
            pip_arg = f"{name}=={p['version']}"
        pip_args.append(pip_arg)

    return pip_args
