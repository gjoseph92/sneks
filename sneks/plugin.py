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
from distributed.diagnostics.plugin import NannyPlugin

if TYPE_CHECKING:
    from distributed.nanny import Nanny

logger = logging.Logger(__name__)


class PoetryDepManager(NannyPlugin):
    name: str = "PoetryDepManager"
    # ^ There should only ever be one instance of this plugin on a cluster at once.
    # So we always use the same name.
    _compressed_lockfile: bytes
    restart: bool = True  # TODO set this in `setup`

    def __init__(self, lockfile: bytes) -> None:
        self._compressed_lockfile = gzip.compress(lockfile)

    async def setup(self, nanny: Nanny) -> None:
        lockfile = await asyncio.to_thread(gzip.decompress, self._compressed_lockfile)
        lockfile_path = Path(nanny.local_dir) / "poetry.lock"

        # TODO skip installation and don't restart if there's already a lockfile and it's up to date.

        with open(lockfile_path, "wb") as f:
            f.write(lockfile)
        del lockfile
        logger.info(f"Wrote lockfile to {lockfile_path}")

        poetry_path = await get_poetry()
        logger.info(f"Poetry available at {poetry_path}")

        logger.info("Installing dependencies from lockfile...")
        await install(poetry_path, lockfile_path)
        logger.info("Installation complete! Restarting worker.")

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


async def get_poetry() -> str:
    if not (poetry_path := shutil.which("poetry")):
        logger.info("Installing Poetry...")
        await run(
            sys.executable,
            "-m",
            "pip",
            "install",
            "poetry",
        )
        poetry_path = shutil.which("poetry")
        assert poetry_path, "Poetry not found after installation!"

        # Make poetry use the global environment
        # TODO do this without a subprocess
        await run(poetry_path, "config", "virtualenvs.create", "false")
    return poetry_path


async def install(poetry_path: str, lockfile_path: Path) -> None:
    cwd = Path.cwd()
    try:
        os.chdir(lockfile_path.parent)
        await run(
            poetry_path, "install", "--remove-untracked", "--no-dev", "--no-root", "-n"
        )
    finally:
        os.chdir(cwd)


async def run(program: str, *args: str, tee: bool = True) -> None:
    call = f"{program} {' '.join(args)}"
    logger.debug(f"Executing {call}")
    proc = await asyncio.create_subprocess_exec(
        program, *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()
    returncode = proc.returncode
    assert returncode is not None

    logger.debug(f"{call} exited with {returncode}")
    if tee:
        if stdout:
            sys.stdout.write(stdout.decode())
        if stderr:
            sys.stderr.write(stderr.decode())

    if returncode != 0:
        raise CalledProcessError(returncode, call, stdout, stderr)
