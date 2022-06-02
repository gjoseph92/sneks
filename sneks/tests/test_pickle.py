import subprocess
import sys
from unittest import mock

import cloudpickle
from distributed.protocol.pickle import dumps

from sneks.pickle import DaskPickleByValue


class Base:
    def __init__(self, msg: str) -> None:
        self.msg = msg

    def print(self) -> None:
        print(self.msg)


class PBV(Base, DaskPickleByValue):
    pass


@mock.patch.object(cloudpickle, "dumps", wraps=cloudpickle.dumps)
def test_pickle_by_value(mock_cp_dumps: mock.Mock):
    obj = PBV("hello world")
    pickled = dumps(obj)
    mock_cp_dumps.assert_called_once()
    assert not hasattr(obj, "_the_first_pickle_is_the_deepest")

    assert dumps(obj) == pickled
    assert not hasattr(obj, "_the_first_pickle_is_the_deepest")

    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            f"import cloudpickle; cloudpickle.loads({pickled!r}).print()",
        ],
        cwd="/",
        capture_output=True,
        check=True,
        text=True,
    )
    assert proc.stdout.strip() == obj.msg


def test_pickle_by_value_needed():
    # If this fails, something is probably wrong with our test setup
    base_pickled = dumps(Base("hello world"))
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            f"import cloudpickle; cloudpickle.loads({base_pickled!r}).print()",
        ],
        cwd="/",
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "ModuleNotFoundError" in proc.stderr
