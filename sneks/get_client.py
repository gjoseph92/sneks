from __future__ import annotations

import subprocess
import sys
from typing import Callable, TypeVar, cast

import coiled
from coiled.utils import parse_wait_for_workers
from distributed.client import Client
from distributed.nanny import Nanny
from distributed.worker import get_client as get_default_client
from rich import print
from typing_extensions import ParamSpec

from sneks.compat import get_backend
from sneks.constants import PROJECT_NAME


def _senv() -> str:
    vi = sys.version_info
    return f"{PROJECT_NAME}-{vi.major}-{vi.minor}-{vi.micro}-full"


P = ParamSpec("P")
T = TypeVar("T")


def _wraps_args(wrapped: Callable[P, T]) -> Callable[[Callable], Callable[P, T]]:
    def inner(wrapper: Callable) -> Callable[P, T]:
        wrapper.__annotations__ = wrapped.__annotations__
        wrapper.__signature__ = wrapped.__signature__
        return cast(Callable[P, T], wrapper)

    return inner


@_wraps_args(coiled.Cluster)
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

    if n_workers := kwargs.get("n_workers"):
        # Scale to requested size, if one was given. This is different from coiled behavior,
        # but ensures a cluster will look the way you're asking for it---more declarative style.
        print(f"[bold white]Scaled to {n_workers} worker(s)[/]")  # TODO improve
        cluster.scale(n_workers)
    else:
        n_workers = cluster._start_n_workers

    # Hack around https://github.com/dask/distributed/issues/7035. Workers that joined while
    # the plugin was getting registered may have missed it.

    # don't want to serialize the whole plugin into the closure
    plugin_name = plugin.name

    async def restart_if_no_dep_manager(dask_worker: Nanny) -> None:
        if plugin_name not in dask_worker.plugins:
            msg = await dask_worker.scheduler.register_nanny()
            for name, plugin in msg["nanny-plugins"].items():  # type: ignore
                await dask_worker.plugin_add(plugin=plugin, name=name)

    # Sadly we have to block on this for consistency's sake.
    # We don't want to return control to the user until we're sure there
    # aren't any workers without the plugin.
    client.run(restart_if_no_dep_manager, nanny=True)

    target = parse_wait_for_workers(n_workers, wait_for_workers)
    print(f"[bold white]Waiting for {target} worker(s)[/]")  # TODO improve
    client.wait_for_workers(target)

    # HACK: make the client "own" the cluster. When the client closes, the cluster
    # object will close too. Whether the actual Coiled cluster shuts down depends on the
    # `shutdown_on_close` argument.
    client._start_arg = None
    return client


# Utils for testing. Remove.
def can_import(module: str):
    import importlib

    importlib.import_module(module)
    return True


def check_import(module: str):
    get_default_client().submit(can_import, module, pure=False).result()
