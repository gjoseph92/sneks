from pathlib import Path

import pytest

from sneks.parse_pdm import current_versions_pdm


def test_current_package_versions():
    env = Path(__file__).parent / "env-for-parsing-pdm"
    with open(env / "pdm.lock", "rb") as f:
        lockfile = f.read()

    assert current_versions_pdm(["dask", "distributed", "yapf"], lockfile=lockfile) == [
        "dask==2022.5.2",
        "distributed==2022.5.2",
        "git+https://github.com/google/yapf.git@c6077954245bc3add82dafd853a1c7305a6ebd20",
    ]

    with pytest.raises(ValueError, match="pdm add blaze scipy"):
        current_versions_pdm(["blaze", "bokeh", "scipy"], lockfile=lockfile)

    # with pytest.raises(ValueError, match="flake8 is only a dev dependency"):
    #     current_versions_pdm(["flake8"], lockfile=lockfile)

    # with pytest.raises(
    #     NotImplementedError, match="mypy is only an optional dependency"
    # ):
    #     current_versions_pdm(["mypy"], lockfile=lockfile)

    with pytest.raises(
        NotImplementedError, match="'sneks' is installed as a path dependency"
    ):
        current_versions_pdm(["sneks"], lockfile=lockfile)
