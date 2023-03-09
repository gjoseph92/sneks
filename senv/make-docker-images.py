"""
DEPRECATED. Do not use?

Used to use this locally to build Docker images. Now they're built automatically
in GitHub Actions. GHA also does cross-arch (ARM and x86) builds, which this script
doesn't do.

Build lots of Docker images for every version of Python.

These are sadly heavy---they're the full Python docker images, so we have things you'd expect
like git and a builtin CA bundle. We then install Poetry and a tiny script. When the image
launches, it installs more pip packages (dask, distributed, bokeh)
via an environment variable, then runs the dask command requested.
"""

from __future__ import annotations

import asyncio
import os
import tarfile
import traceback
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from aiodocker import Docker
from rich import print

from sneks.constants import DOCKER_IMAGE_PATTERN

PY_VERSIONS = [
    "3.8.0",
    "3.8.1",
    "3.8.2",
    "3.8.3",
    "3.8.4",
    "3.8.5",
    "3.8.6",
    "3.8.7",
    "3.8.8",
    "3.8.9",
    "3.8.10",
    "3.8.11",
    "3.8.12",
    "3.8.13",
    "3.8.14",
    "3.9.0",
    "3.9.1",
    "3.9.2",
    "3.9.4",
    "3.9.5",
    "3.9.6",
    "3.9.7",
    "3.9.8",
    "3.9.9",
    "3.9.10",
    "3.9.11",
    "3.9.12",
    "3.9.13",
    "3.9.14",
    "3.10.0",
    "3.10.1",
    "3.10.2",
    "3.10.3",
    "3.10.4",
    "3.10.5",
    "3.10.6",
    "3.10.7",
    "3.10.8",
    "3.10.9",
    "3.10.10",
]


@contextmanager
def tar_docker_context() -> Iterator[Path]:
    "aiodocker annoyingly only lets you build from a tarball, not a local directory"
    here = Path(__file__).parent
    tarpath = here / "context.tar"
    with tarfile.open(tarpath, mode="w:gz") as tar:
        tar.add(here / "Dockerfile", "Dockerfile")
        tar.add(here / "fake-entrypoint.sh", "fake-entrypoint.sh")

    try:
        yield tarpath
    finally:
        tarpath.unlink(missing_ok=True)


async def make_image(docker: Docker, tarpath: Path, py_version: str) -> str:
    major, minor, micro = py_version.split(".")
    name = DOCKER_IMAGE_PATTERN.format(major=major, minor=minor, micro=micro)
    base_image = f"python:{py_version}"
    print(f"Building image {name!r} from {base_image!r}")
    try:
        with tarpath.open("rb") as f:
            await docker.images.build(
                fileobj=f,
                encoding="gzip",
                buildargs={"IMAGE": base_image},
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
        print(f"Deleting image {name}")
        await docker.images.delete(name)
        print(f"Image {name} deleted")
    except Exception as exc:
        print(f"[bold red]Error with image {name}: {exc}")
        traceback.print_exc()
        raise

    print(f"[bold blue]Image {name} complete[/]")
    return name


async def make_envs(
    docker: Docker,
    tarpath: Path,
    versions: list[str],
) -> None:
    docker_builds: asyncio.Queue[str] = asyncio.Queue()

    async def _docker():
        while True:
            version = await docker_builds.get()
            try:
                await make_image(docker, tarpath, version)
            except Exception:
                pass
            finally:
                docker_builds.task_done()

    tasks = [asyncio.create_task(_docker()) for _ in range(os.cpu_count() or 2)]

    for v in versions:
        docker_builds.put_nowait(v)

    await docker_builds.join()
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


async def main():
    with tar_docker_context() as tarpath:
        async with Docker() as docker:
            await make_envs(docker, tarpath, PY_VERSIONS)


if __name__ == "__main__":
    asyncio.run(main())
