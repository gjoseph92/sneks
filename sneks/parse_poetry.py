from __future__ import annotations

import tomli


def current_versions_poetry(packages: list[str], lockfile: bytes) -> list[str]:
    "Determine what versions of ``packages`` are currently installed by parsing the lockfile"
    lock = tomli.loads(lockfile.decode())
    pset = set(packages)
    matches = {name: p for p in lock["package"] if (name := p["name"]) in pset}
    if missing := sorted(pset - matches.keys()):
        raise ValueError(
            f"Required packages {missing} are not dependencies of your environment. "
            "These packages must be installed to create a dask cluster. "
            f"Run `poetry add {' '.join(missing)}` to install them."
        )

    pip_args: list[str] = []
    for name, p in matches.items():
        if p.get("category", "") == "dev":
            raise ValueError(
                f"Required package {name} is only a dev dependency. "
                "Dev dependencies will not be installed on the cluster.\n"
                f"Upgrade this to a full dependency with `poetry add {name}`, or better, manually move it "
                "from the `tool.poetry.dev-dependencies` section to the `tool.poetry.dependencies` section "
                "of your `pyproject.toml`)."
            )
        if p.get("optional", False):
            raise NotImplementedError(
                f"Required package {name} is only an optional dependency. "
                "Optional dependencies will not be installed on the cluster. "
                "Please open an issue, since perhaps they should be.\n"
                "For now, please make this a non-optional dependency."
            )
        if source := p.get("source"):
            if (stype := source["type"]) != "git":
                if stype == "directory":
                    raise NotImplementedError(
                        f"Required package {name!r} is installed as a path dependency. "
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
            pip_arg = f"git+{source['url']}@{source['resolved_reference']}"
        else:
            pip_arg = f"{name}=={p['version']}"
        pip_args.append(pip_arg)

    return pip_args
