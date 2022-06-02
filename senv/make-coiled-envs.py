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
import tarfile
import traceback
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from aiodocker import Docker
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

DOCKER_USERNAME = "jabriel"
PROJECT_NAME = "sneks"


@contextmanager
def tar_docker_context() -> Iterator[Path]:
    "aiodocker annoyingly only lets you build from a tarball, not a local directory"
    here = Path(__file__).parent
    tarpath = here / "context.tar"
    with tarfile.open(tarpath, mode="w:gz") as tar:
        tar.add(here / "Dockerfile", "Dockerfile")
        tar.add(here / "fake-dask.sh", "fake-dask.sh")

    try:
        yield tarpath
    finally:
        tarpath.unlink(missing_ok=True)


async def make_image(docker: Docker, tarpath: Path, py_version: str) -> str:
    name = f"{DOCKER_USERNAME}/{PROJECT_NAME}:{py_version}"
    print(f"Building image {name}")
    try:
        with tarpath.open("rb") as f:
            await docker.images.build(
                fileobj=f,
                encoding="gzip",
                buildargs={"PY_VERSION": py_version},
                tag=name,
                quiet=True,
            )
        print(f"Pushing image {name}")
        # TODO figure out how to use aiodocker here.
        # Not sure how to deal with auth.
        proc = await asyncio.create_subprocess_shell(
            f"docker image push {name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            if stdout:
                print(stdout.decode())
            if stderr:
                print(stderr.decode())
            raise RuntimeError("Image push failed")
    except Exception as exc:
        print(f"[bold red]Error with image {name}: {exc}")
        traceback.print_exc()

    print(f"[bold blue]Image {name} complete[/]")
    return name


async def make_env(
    cloud: Cloud[Async],
    image: str,
) -> str:
    name = image.split("/")[1].replace(":", "-").replace(".", "-")
    print(f"Building senv {name}")
    log = io.StringIO()
    try:
        await cloud.create_software_environment(
            name,
            account="gjoseph92",
            container=image,
            log_output=log,
        )
    except Exception as exc:
        print(f"[bold red]Error building {name}[/]: {exc}")
        print(log.getvalue())
        raise

    print(f"[bold green]Senv {name} succeeded!")
    return name


async def make_envs(
    cloud: Cloud[Async],
    docker: Docker,
    tarpath: Path,
    versions: list[str],
    *,
    concurrency: int = 6,
) -> None:
    docker_builds: asyncio.Queue[str] = asyncio.Queue()
    senv_creates: asyncio.Queue[str] = asyncio.Queue()

    async def _docker():
        while True:
            version = await docker_builds.get()
            image = await make_image(docker, tarpath, version)
            await senv_creates.put(image)
            docker_builds.task_done()

    async def _senv():
        while True:
            image = await senv_creates.get()
            await make_env(cloud, image)
            senv_creates.task_done()

    tasks = [asyncio.create_task(_docker()) for _ in range(8)]  # TODO ncores
    tasks += [asyncio.create_task(_senv()) for _ in range(concurrency)]

    for v in versions:
        docker_builds.put_nowait(v)

    await asyncio.gather(docker_builds.join(), senv_creates.join())
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


async def main():
    with tar_docker_context() as tarpath:
        async with Cloud(asynchronous=True) as cloud, Docker() as docker:
            await make_envs(cloud, docker, tarpath, PY_VERSIONS)


if __name__ == "__main__":
    asyncio.run(main())
