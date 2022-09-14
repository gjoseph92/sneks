from __future__ import annotations

import subprocess
import sys

import coiled
from coiled.utils import parse_wait_for_workers
from distributed.client import Client
from distributed.worker import get_client as get_default_client
from rich import print

from sneks.compat import get_backend
from sneks.constants import PROJECT_NAME


def _senv() -> str:
    vi = sys.version_info
    return f"{PROJECT_NAME}-{vi.major}-{vi.minor}-{vi.micro}-full"


def get_client(**kwargs) -> Client:
    """
    Launch a dask cluster in the cloud compatible with your current Poetry or PDM environment.

    All keyword arguments are forwarded to `coiled.Cluster`.

    You must be in the root directory of a Poetry or PDM project, with a ``pyproject.toml``
    and ``poetry.lock`` or ``pdm.lock`` file. All non-dev, non-optional dependencies listed in
    the lockfile will be installed on the cluster when you connect to it, then the workers
    will restart if necessary.
    """
    # TODO deal with async
    # TODO paramspec for signature

    wait_for_workers = kwargs.pop("wait_for_workers", None)
    environ: dict[str, str] = kwargs.pop("environ", {})

    plugin, new_env = get_backend()
    environ.update(new_env)

    cluster = coiled.Cluster(
        software=_senv(), environ=environ, **kwargs, wait_for_workers=False
    )
    client = Client(cluster)
    print(
        "[bold white]Uploading lockfile and installing dependencies on running workers[/]"
    )  # TODO improve
    try:
        client.register_worker_plugin(plugin)
    except subprocess.CalledProcessError as e:
        print("[bold red]Dependency installation failed[/]")  # TODO improve
        print("[stdout]", e.stdout.decode())
        print("[stderr]", e.stderr.decode())
        raise
    target = parse_wait_for_workers(cluster._start_n_workers, wait_for_workers)
    print(f"[bold white]Waiting for {target} worker(s)[/]")  # TODO improve
    cluster.scale(target)
    client.wait_for_workers(target)
    return client


# Utils for testing. Remove.
def can_import(module: str):
    import importlib

    importlib.import_module(module)
    return True


def check_import(module: str):
    get_default_client().submit(can_import, module, pure=False).result()
