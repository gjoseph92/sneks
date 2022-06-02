import importlib
import subprocess
import sys
import time
from pathlib import Path
from unittest import mock

import cloudpickle
import pytest
from distributed.client import Client
from distributed.protocol.pickle import dumps

from sneks.plugin import PoetryDepManager

pytest_plugins = ["docker_compose"]


class TestPickle:
    @mock.patch.object(cloudpickle, "dumps", wraps=cloudpickle.dumps)
    def test_pickle_by_value(self, mock_cp_dumps: mock.Mock):
        obj = PoetryDepManager(b"hello world")
        pickled = dumps(obj)
        mock_cp_dumps.assert_called_once()
        assert not hasattr(obj, "_the_first_pickle_is_the_deepest")

        assert dumps(obj) == pickled
        assert not hasattr(obj, "_the_first_pickle_is_the_deepest")

        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                f"import cloudpickle; print(cloudpickle.loads({pickled!r})._compressed_lockfile)",
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
                f"import cloudpickle; print(cloudpickle.loads({base_pickled!r}).msg)",
            ],
            cwd="/",
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert "ModuleNotFoundError" in proc.stderr


def test_plugin(function_scoped_container_getter):
    time.sleep(1)  # FIXME stream is closed during handshake without this, wtf??
    network_info = function_scoped_container_getter.get("scheduler").network_info[0]
    with Client(
        f"tcp://{network_info.hostname}:{network_info.host_port}", set_as_default=False
    ) as client:

        def can_import(module: str):
            importlib.import_module(module)
            return True

        with pytest.raises(ImportError):
            print(client.submit(can_import, "black").result())

        # Lockfile was generated from:
        # mkdir test
        # cd test
        # poetry init -n
        # poetry add black
        with open(Path(__file__).parent / "poetry.lock.fixture", "rb") as f:
            lockfile = f.read()

        plugin = PoetryDepManager(lockfile)
        client.register_worker_plugin(plugin)

        assert client.submit(can_import, "black").result() is True
