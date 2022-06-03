from __future__ import annotations

import subprocess
import sys

import coiled
import tomli
from coiled.utils import parse_wait_for_workers
from distributed.client import Client
from distributed.worker import get_client as get_default_client
from rich import print

from sneks.plugin import PoetryDepManager

PROJECT_NAME = "sneks"


def _current_package_versions(*packages: str, lockfile: bytes) -> list[str]:
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
            if source["type"] != "git":
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


def _environ(lockfile: bytes) -> dict[str, str]:
    return {
        "PIP_PACKAGES": " ".join(
            _current_package_versions("dask", "distributed", "bokeh", lockfile=lockfile)
        )
    }


def _senv() -> str:
    vi = sys.version_info
    return f"{PROJECT_NAME}-{vi.major}-{vi.minor}-{vi.micro}"


def _poetry_files() -> tuple[bytes, bytes]:
    # FIXME much to do here. Actually find them, validate, etc.
    with open("pyproject.toml", "rb") as f:
        pyproject = f.read()
    with open("poetry.lock", "rb") as f:
        lockfile = f.read()
    return pyproject, lockfile


def get_client(**kwargs) -> Client:
    """
    Launch a dask cluster in the cloud compatible with your current Poetry environment.

    All keyword arguments are forwarded to `coiled.Cluster`.

    You must be in the root directory of a Poetry project, with a ``pyproject.toml``
    and ``poetry.lock`` file. All non-dev, non-optional dependencies listed in the
    lockfile will be installed on the cluster when you connect to it, then the workers
    will restart if necessary.
    """
    # TODO deal with async
    # TODO paramspec for signature

    pyproject, lockfile = _poetry_files()

    wait_for_workers = kwargs.pop("wait_for_workers", None)
    environ: dict[str, str] = kwargs.pop("environ", {})
    environ.update(_environ(lockfile))

    cluster = coiled.Cluster(
        software=_senv(), environ=environ, **kwargs, wait_for_workers=False
    )
    client = Client(cluster)
    print(
        "[bold white]Uploading lockfile and installing dependencies on running workers[/]"
    )  # TODO improve
    try:
        client.register_worker_plugin(PoetryDepManager(pyproject, lockfile))
    except subprocess.CalledProcessError as e:
        print("[bold red]Dependency installation failed[/]")  # TODO improve
        print("[stdout]", e.stdout.decode())
        print("[stderr]", e.stderr.decode())
        raise
    target = parse_wait_for_workers(cluster._start_n_workers, wait_for_workers)
    print(f"[bold white]Waiting for {target} worker(s)[/]")  # TODO improve
    client.wait_for_workers(target)
    return client


# Utils for testing. Remove.
def can_import(module: str):
    import importlib

    importlib.import_module(module)
    return True


def check_import(module: str):
    get_default_client().submit(can_import, module, pure=False).result()
