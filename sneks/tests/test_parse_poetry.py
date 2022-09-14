from pathlib import Path

import pytest

from sneks.parse_poetry import current_versions_poetry


def test_current_package_versions():
    env = Path(__file__).parent / "env-for-parsing-poetry"
    with open(env / "poetry.lock", "rb") as f:
        lockfile = f.read()

    assert current_versions_poetry(
        ["dask", "distributed", "yapf"], lockfile=lockfile
    ) == [
        "dask==2022.5.2",
        "distributed==2022.5.2",
        "git+https://github.com/google/yapf.git@c6077954245bc3add82dafd853a1c7305a6ebd20",
    ]

    with pytest.raises(ValueError, match="poetry add blaze scipy"):
        current_versions_poetry(["blaze", "bokeh", "scipy"], lockfile=lockfile)

    with pytest.raises(ValueError, match="flake8 is only a dev dependency"):
        current_versions_poetry(["flake8"], lockfile=lockfile)

    with pytest.raises(
        NotImplementedError, match="mypy is only an optional dependency"
    ):
        current_versions_poetry(["mypy"], lockfile=lockfile)

    with pytest.raises(
        NotImplementedError, match="'sneks' is installed as a path dependency"
    ):
        current_versions_poetry(["sneks"], lockfile=lockfile)
