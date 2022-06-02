"""
Build lots of Coiled software environments for every version of Python.

These are extremely lightweight for fast cluster startup, and just contain Python and Poetry.

FIXME though public, they can't actually be run by other v2 users!
This whole strategy won't work right now.
We could use public docker images, but dockerhub has ratelimiting.
"""

from __future__ import annotations

import asyncio
import io
import sys

from coiled.core import Async, Cloud
from rich import print

PY_VERSIONS = [
    # "3.10.4",
    # "3.10.2",
    # "3.10.1",
    # "3.10.0",
    # "3.9.13",
    # "3.9.12",
    # "3.9.10",
    # "3.9.9",
    # "3.9.7",
    # "3.9.6",
    # "3.9.5",
    "3.9.4",
    "3.9.2",
    "3.9.1",
    "3.9.0",
    # "3.8.13",
    # "3.8.12",
    # "3.8.10",
    # "3.8.8",
    # "3.8.6",
    # "3.8.5",
    # "3.8.4",
    # "3.8.3",
    # "3.8.2",
    # "3.8.1",
    # "3.8.0",
]


async def make_env(
    cloud: Cloud[Async],
    py_version: str,
    docker: bool = False,
) -> str:
    name = f"sneks-{py_version.replace('.', '-')}"
    if docker:
        name += "-slim"  # would love to use alpine, it's way smaller, but many wheels don't work
    print(f"Building senv {name}")
    log = io.StringIO()
    try:
        if docker:
            kwargs = {"container": f"python:{py_version}-slim"}
        else:
            kwargs = {
                "conda": {
                    "channels": ["conda-forge"],
                    "dependencies": [f"python={py_version}", "poetry"],
                }
            }
        await cloud.create_software_environment(
            name,
            account="gjoseph92",
            log_output=log,
            **kwargs,
        )
    except Exception as exc:
        print(f"[bold red]Error building {name}[/]: {exc}")
        print(log.getvalue())
        raise

    print(f"[bold green]Senv {name} succeeded!")
    return name


async def make_envs(
    cloud: Cloud[Async],
    versions: list[str],
    *,
    docker: bool = False,
    concurrency: int = 6,
) -> list[str]:
    sem = asyncio.Semaphore(concurrency)

    async def make(py_version: str):
        async with sem:
            return await make_env(cloud, py_version, docker)

    results = await asyncio.gather(*(make(v) for v in versions), return_exceptions=True)
    return [n for n in results if isinstance(n, str)]


async def main():
    if len(sys.argv) == 2:
        assert sys.argv[-1] == "--docker", "To use docker base, pass `--docker`"
        docker = True
    else:
        docker = False
    async with Cloud(asynchronous=True) as cloud:
        await make_envs(cloud, PY_VERSIONS, docker=docker)


if __name__ == "__main__":
    asyncio.run(main())
