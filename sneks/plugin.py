from __future__ import annotations

import asyncio
import gzip
import importlib
import logging
import os
import shutil
import sys
from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING

import cloudpickle
from distributed.compatibility import to_thread  # type: ignore
from distributed.diagnostics.plugin import NannyPlugin

if TYPE_CHECKING:
    from distributed.nanny import Nanny

logger = logging.Logger(__name__)


class PoetryDepManager(NannyPlugin):
    name: str = "PoetryDepManager"
    # ^ There should only ever be one instance of this plugin on a cluster at once.
    # So we always use the same name.
    _compressed_lockfile: bytes

    def __init__(self, pyproject: bytes, lockfile: bytes) -> None:
        self._compressed_pyproject = gzip.compress(pyproject)
        self._compressed_lockfile = gzip.compress(lockfile)

    async def setup(self, nanny: Nanny) -> None:
        workdir = Path(nanny.local_directory)
        pyproject_path = workdir / "pyproject.toml"
        lockfile_path = workdir / "poetry.lock"
        await asyncio.gather(
            write_compressed_file(self._compressed_pyproject, pyproject_path),
            write_compressed_file(self._compressed_lockfile, lockfile_path),
        )

        # TODO skip installation and don't restart if there's already a lockfile and it's up to date.

        poetry_path = await get_poetry()
        print(f"Poetry available at {poetry_path}")

        # Make poetry use the global environment
        # TODO do this without a subprocess
        # TODO only do this once
        await run(poetry_path, "config", "virtualenvs.create", "false")
        print("Poetry configured to use global environment")

        print("Installing dependencies from lockfile...")
        self.restart = await install(poetry_path, workdir)
        print(
            "Installation complete! Restarting worker."
            if self.restart
            else "No dependencies to install or update"
        )

    def __getstate__(self) -> dict:
        """
        Make this object unpickleable to dask without its package being installed on workers, via a horrible hack.
        """
        # HACK, awful horrible hack.
        # The implementation of `distributed.protocol.pickle.dumps` currently tries to plain `pickle.dumps`
        # the object. If that raises an error, then it tries `cloudpickle.dumps`.
        # We game this code structure by raising an error every other time we're pickled, forcing the
        # `cloudpickle.dumps` codepath and then succeeding on that one.
        if getattr(self, "_the_first_pickle_is_the_deepest", True):
            self._the_first_pickle_is_the_deepest = False
            raise RuntimeError("cloudpickle time!")
        else:
            del self._the_first_pickle_is_the_deepest

            # Very awkward, but the only way to tell cloudpickle to pickle something by value
            # is by passing it the module whose members you want pickled by value.
            module = importlib.import_module(self.__module__)
            cloudpickle.register_pickle_by_value(module)

            return self.__dict__


async def write_compressed_file(data: bytes, path: Path) -> None:
    def _write():
        with open(path, "wb") as f:
            f.write(gzip.decompress(data))

    await to_thread(_write)
    print(f"Wrote to {path}")


async def get_poetry() -> str:
    poetry_path = Path.home() / ".local" / "bin" / "poetry"
    if poetry_path.is_file():
        return str(poetry_path)

    elif not (poetry_path := shutil.which("poetry")):
        raise RuntimeError("cannot find poetry installation")
        # We don't want to install poetry in the main environment,
        # because then it might try to remove itself if it's not a dep
        # of the user's environment (it almost certainly isn't).

        # print("Installing Poetry...")
        # await run(
        #     sys.executable,
        #     "-m",
        #     "pip",
        #     "install",
        #     "poetry",
        # )
        # poetry_path = shutil.which("poetry")
        # assert poetry_path, "Poetry not found after installation!"

    return poetry_path


async def install(poetry_path: str, workdir: Path) -> bool:
    cwd = Path.cwd()
    try:
        os.chdir(workdir)
        out, err = await run(
            poetry_path,
            "install",
            "--remove-untracked",
            "--no-dev",
            "--no-root",
            "-n",
        )
        # HACK we can do better than this text parsing to decide
        # whether to restart or not
        return b"No dependencies to install or update" not in out
    finally:
        os.chdir(cwd)


async def run(program: str | Path, *args: str, tee: bool = True) -> tuple[bytes, bytes]:
    call = f"{program} {' '.join(args)}"
    print(f"Executing {call}")
    proc = await asyncio.create_subprocess_exec(
        program, *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()
    returncode = proc.returncode
    assert returncode is not None

    print(f"{call} exited with {returncode}")
    if tee:
        if stdout:
            sys.stdout.write(stdout.decode())
        if stderr:
            sys.stderr.write(stderr.decode())

    if returncode != 0:
        raise CalledProcessError(returncode, call, stdout, stderr)
    return stdout, stderr
