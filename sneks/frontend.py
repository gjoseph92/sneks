from __future__ import annotations

import importlib.metadata
import sys

import coiled
from coiled.utils import parse_wait_for_workers
from distributed.client import Client
from distributed.worker import get_client as get_default_client

from sneks.plugin import PoetryDepManager

PROJECT_NAME = "sneks"


def _current_package_versions(*packages: str) -> dict[str, str]:
    # TODO this almost certainly won't work with git URLs, etc.
    # Maybe we'd want to parse this from the lockfile?
    return {p: importlib.metadata.version(p) for p in packages}


def _environ() -> dict[str, str]:
    return {
        "PIP_PACKAGES": " ".join(
            f"{p}=={v}"
            for p, v in _current_package_versions(
                "dask", "distributed", "bokeh"
            ).items()
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
    "Launch a dask cluster in the cloud compatible with your current Poetry environment"
    # TODO deal with async
    # TODO paramspec for signature

    wait_for_workers = kwargs.pop("wait_for_workers", None)
    environ: dict[str, str] = kwargs.pop("environ", {})
    environ.update(_environ())
    cluster = coiled.Cluster(
        software=_senv(), environ=environ, **kwargs, wait_for_workers=False
    )
    client = Client(cluster)
    print("Uploading & installing dependencies on running workers")  # TODO improve
    client.register_worker_plugin(PoetryDepManager(*_poetry_files()))
    target = parse_wait_for_workers(cluster._start_n_workers, wait_for_workers)
    print(f"Waiting for {target} worker(s)")  # TODO improve
    client.wait_for_workers(target)
    return client


# Utils for testing. Remove.
def can_import(module: str):
    import importlib

    importlib.import_module(module)
    return True


def check_import(module: str):
    get_default_client().submit(can_import, module, pure=False).result()
