from __future__ import annotations

import importlib.metadata
import sys

import coiled
from distributed.client import Client

from sneks.plugin import PoetryDepManager

PROJECT_NAME = "sneks"


def _current_package_versions(*packages: str) -> dict[str, str]:
    # TODO this almost certainly won't work with git URLs, etc.
    # Maybe we'd want to parse this from the lockfile?
    return {p: importlib.metadata.version(p) for p in packages}


def _environ() -> dict[str, str]:
    return {
        "PIP_PACKAGES": " ".join(
            f"{p}={v}"
            for p, v in _current_package_versions("dask", "distributed").items()
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
    # TODO deal with async
    # TODO paramspec for signature

    environ: dict[str, str] = kwargs.pop("environ", {})
    environ.update(_environ())
    cluster = coiled.Cluster(
        software=_senv(), environ=environ, **kwargs, wait_for_workers=False
    )
    client = Client(cluster)
    client.register_worker_plugin(PoetryDepManager(*_poetry_files()))
    return client
