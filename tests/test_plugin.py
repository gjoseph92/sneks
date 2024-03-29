import asyncio
import importlib.metadata
import os
import subprocess
import sys
import time
from pathlib import Path
from unittest import mock

import cloudpickle
import pytest
from distributed.client import Client
from distributed.protocol.pickle import dumps

from sneks.plugin import PdmDepManager, PoetryDepManager

from .update_test_envs import PIP_OVERRIDES, update_test_envs

pytest_plugins = ["docker_compose"]


class TestPickle:
    @mock.patch.object(cloudpickle, "dumps", wraps=cloudpickle.dumps)
    def test_pickle_by_value(self, mock_cp_dumps: mock.Mock):
        obj = PoetryDepManager(b"hello", b"world")
        pickled = dumps(obj)
        mock_cp_dumps.assert_called_once()
        assert not hasattr(obj, "_the_first_pickle_is_the_deepest")

        assert dumps(obj) == pickled
        assert not hasattr(obj, "_the_first_pickle_is_the_deepest")

        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import cloudpickle; "
                    "import sys; "
                    "sys.modules['sneks'] = None; "
                    f"print(cloudpickle.loads({pickled!r})._compressed_lockfile)"
                ),
            ],
            cwd="/",
            capture_output=True,
            check=True,
            text=True,
        )
        assert proc.stdout.strip() == repr(obj._compressed_lockfile)

    class Basic:
        def __init__(self, msg: str) -> None:
            self.msg = msg

    def test_pickle_by_value_needed(self):
        # If this fails, something is probably wrong with our test setup
        base_pickled = dumps(self.Basic("hello world"))
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import cloudpickle; "
                    "import sys; "
                    "sys.modules['sneks'] = None; "
                    f"print(cloudpickle.loads({base_pickled!r}).msg)"
                ),
            ],
            cwd="/",
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0, proc.stdout
        assert "ModuleNotFoundError" in proc.stderr


# NOTE: see conftest.py for how we set env vars to inject into the docker-compose build process


@pytest.fixture(scope="session")
def updated_test_envs():
    "Ensure the versions in ``env-for-running-*`` match what's installed locally."
    update_test_envs()


@pytest.mark.parametrize("plugin_type", [PoetryDepManager, PdmDepManager])
def test_plugin(updated_test_envs, function_scoped_container_getter, plugin_type):
    network_info = function_scoped_container_getter.get("scheduler").network_info[0]
    addr = f"tcp://{network_info.hostname}:{network_info.host_port}"

    # Wait for scheduler to actually start. idk why client retries don't work here.
    start = time.monotonic()
    while time.monotonic() - start < 10:
        try:
            client = Client(addr, set_as_default=False)
        except (OSError, asyncio.TimeoutError):
            print("did not respond")
            time.sleep(1)
        else:
            break
    else:
        pytest.fail("Could not connect in 10s")

    with client:

        def version_of(module: str) -> str:
            return importlib.metadata.version(module)

        # See `conftest.py` for where `yapf` gets added to docker image
        assert client.submit(version_of, "yapf", pure=False).result(timeout=5)

        for pkg, version in PIP_OVERRIDES.items():
            assert (
                client.submit(version_of, pkg, pure=False).result(timeout=5) == version
            )

        with pytest.raises(importlib.metadata.PackageNotFoundError):
            print(client.submit(version_of, "black").result())

        root = (
            Path(__file__).parent / f"env-for-running-{plugin_type.TOOL_NAME.lower()}"
        )
        with open(root / "pyproject.toml", "rb") as f:
            pyproject = f.read()
        with open(root / plugin_type.LOCKFILE_NAME, "rb") as f:
            lockfile = f.read()

        pids = client.run(os.getpid)
        plugin = plugin_type(pyproject, lockfile)
        try:
            client.register_worker_plugin(plugin)
        except subprocess.CalledProcessError as e:
            print("[stdout]", e.stdout.decode())
            print("[stderr]", e.stderr.decode())
            raise

        # See `update_test_envs.py` for where `black` gets added to poetry reqs
        assert client.submit(version_of, "black", pure=False).result(
            timeout=5
        ) == version_of("black")

        with pytest.raises(importlib.metadata.PackageNotFoundError):
            print(client.submit(version_of, "yapf").result())

        # Workers were restarted
        assert client.run(os.getpid) != pids

        # Registering with same deps doesn't cause restart
        pids = client.run(os.getpid)
        try:
            client.register_worker_plugin(plugin)
        except subprocess.CalledProcessError as e:
            print("[stdout]", e.stdout.decode())
            print("[stderr]", e.stderr.decode())
            raise
