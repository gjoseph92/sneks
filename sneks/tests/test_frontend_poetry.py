from pathlib import Path

import pytest

from sneks.frontend_poetry import _current_package_versions


def test_current_package_versions():
    env = Path(__file__).parent / "env-for-parsing-poetry"
    with open(env / "poetry.lock", "rb") as f:
        lockfile = f.read()

    assert _current_package_versions(
        ["dask", "distributed", "yapf"], lockfile=lockfile
    ) == [
        "dask==2022.5.2",
        "distributed==2022.5.2",
        "git+https://github.com/google/yapf.git@c6077954245bc3add82dafd853a1c7305a6ebd20",
    ]

    with pytest.raises(ValueError, match="poetry add blaze scipy"):
        _current_package_versions(["blaze", "bokeh", "scipy"], lockfile=lockfile)

    with pytest.raises(ValueError, match="flake8 is only a dev dependency"):
        _current_package_versions(["flake8"], lockfile=lockfile)

    with pytest.raises(
        NotImplementedError, match="mypy is only an optional dependency"
    ):
        _current_package_versions(["mypy"], lockfile=lockfile)
