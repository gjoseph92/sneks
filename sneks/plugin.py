from __future__ import annotations

import asyncio
import gzip
import importlib
import logging
import os
import shutil
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, ClassVar

import cloudpickle
from distributed.compatibility import to_thread  # type: ignore
from distributed.diagnostics.plugin import NannyPlugin

if TYPE_CHECKING:
    from distributed.nanny import Nanny

logger = logging.Logger(__name__)


class DepManagerBase(NannyPlugin, ABC):
    name: str = "DepManager"
    # ^ There should only ever be one instance of this plugin on a cluster at once.
    # So we always use the same name.
    _compressed_lockfile: bytes

    LOCKFILE_NAME: ClassVar[str]
    TOOL_NAME: ClassVar[str]

    def __init__(self, pyproject: bytes, lockfile: bytes) -> None:
        self._compressed_pyproject = gzip.compress(pyproject)
        self._compressed_lockfile = gzip.compress(lockfile)

    def get_tool_path(self) -> Path:
        "Get path to the installation tool"
        tool_path = Path.home() / ".local" / "bin" / self.TOOL_NAME.lower()
        if tool_path.is_file():
            return tool_path

        if tool_path_which := shutil.which(self.TOOL_NAME.lower()):
            return Path(tool_path_which)

        raise RuntimeError(f"cannot find {self.TOOL_NAME} installation")

    async def setup_tool(self, *, tool_path: Path, workdir: Path) -> None:
        "Do any setup needed before installation"
        return

    @abstractmethod
    async def install(self, *, tool_path: Path, workdir: Path) -> bool:
        "Do installation, return whether to restart"
        raise NotImplementedError

    async def setup(self, nanny: Nanny) -> None:
        workdir = Path(nanny.local_directory)
        pyproject_path = workdir / "pyproject.toml"
        lockfile_path = workdir / self.LOCKFILE_NAME
        await asyncio.gather(
            write_compressed_file(self._compressed_pyproject, pyproject_path),
            write_compressed_file(self._compressed_lockfile, lockfile_path),
        )

        # TODO skip installation and don't restart if there's already a lockfile and it's up to date.

        tool_path = self.get_tool_path().absolute()
        print(f"{self.TOOL_NAME} available at {tool_path}")

        await self.setup_tool(tool_path=tool_path, workdir=workdir)

        self.restart = await self.install(tool_path=tool_path, workdir=workdir)
        print(
            "Installation complete! Restarting worker."
            if self.restart
            else "No dependencies to install or update"
        )

    def __getstate__(self) -> dict:
        """
        Make this object unpickleable to dask without its package being installed on workers, via a horrible hack.

        This avoids needing `sneks` to actually be installed on the cluster, just on the client side.
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

    @staticmethod
    async def run(
        program: str | Path,
        *args: str,
        tee: bool = True,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> tuple[bytes, bytes]:
        call = f"{program} {' '.join(args)}"
        print(f"Executing {call}")
        proc = await asyncio.create_subprocess_exec(
            program,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
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


async def write_compressed_file(data: bytes, path: Path) -> None:
    def _write():
        with open(path, "wb") as f:
            f.write(gzip.decompress(data))

    await to_thread(_write)
    print(f"Wrote to {path}")


# Concrete implementations
##########################
#
# Sadly, these all have to be in the same file for pickle-by-value to work.
# Otherwise, they'd still reference an import from sneks for the base class.


class PoetryDepManager(DepManagerBase):
    LOCKFILE_NAME: ClassVar[str] = "poetry.lock"
    TOOL_NAME: ClassVar[str] = "Poetry"

    async def setup_tool(self, *, tool_path: Path, workdir: Path) -> None:
        "Make poetry use the global environment"
        # TODO do this without a subprocess
        # TODO only do this once
        await self.run(tool_path, "config", "virtualenvs.create", "false")
        print("Poetry configured to use global environment")

    async def install(self, *, tool_path: Path, workdir: Path) -> bool:
        cwd = Path.cwd()
        try:
            os.chdir(workdir)
            out, err = await self.run(
                tool_path,
                "install",
                "--sync",
                "--only main",
                "--no-root",
                "-n",
            )
            # HACK we can do better than this text parsing to decide
            # whether to restart or not
            return b"Updating" in out or b"Removing" in out
        finally:
            os.chdir(cwd)


class PdmDepManager(DepManagerBase):
    LOCKFILE_NAME: ClassVar[str] = "pdm.lock"
    TOOL_NAME: ClassVar[str] = "PDM"

    async def install(self, *, tool_path: Path, workdir: Path) -> bool:
        await self.run(
            tool_path,
            "info",
            cwd=workdir,
            env=dict(VIRTUAL_ENV=str(Path(sys.executable).parent.parent.absolute())),
        )
        out, err = await self.run(
            tool_path,
            "sync",
            "--clean",
            "--no-self",
            "--no-isolation",
            cwd=workdir,
            # HACK: trick PDM into thinking it's running in a virtualenv so it installs
            # into system python
            env=dict(VIRTUAL_ENV=str(Path(sys.executable).parent.parent.absolute())),
        )
        # HACK we can do better than this text parsing to decide
        # whether to restart or not
        return b"nothing to do" not in out
