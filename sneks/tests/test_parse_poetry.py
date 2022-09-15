from pathlib import Path

import pytest

from sneks.parse_poetry import current_versions_poetry


def test_current_package_versions():
    env = Path(__file__).parent / "env-for-parsing-poetry"
    with open(env / "poetry.lock", "rb") as f:
        lockfile = f.read()

    assert set(
        current_versions_poetry(
            {"dask", "distributed", "yapf"}, set(), lockfile=lockfile
        )
    ) == {
        "dask==2022.5.2",
        "distributed==2022.5.2",
        "git+https://github.com/google/yapf.git@c6077954245bc3add82dafd853a1c7305a6ebd20",
    }

    assert set(
        current_versions_poetry({"dask", "distributed"}, {"yapf"}, lockfile=lockfile)
    ) == {
        "dask==2022.5.2",
        "distributed==2022.5.2",
        "git+https://github.com/google/yapf.git@c6077954245bc3add82dafd853a1c7305a6ebd20",
    }

    assert set(
        current_versions_poetry(
            {"dask", "distributed"}, {"bokeh", "foo"}, lockfile=lockfile
        )
    ) == {
        "dask==2022.5.2",
        "distributed==2022.5.2",
        "bokeh==2.4.3",
    }

    with pytest.raises(ValueError, match="poetry add blaze scipy"):
        current_versions_poetry({"blaze", "bokeh", "scipy"}, set(), lockfile=lockfile)

    with pytest.raises(ValueError, match="flake8 is only a dev dependency"):
        current_versions_poetry({"flake8"}, set(), lockfile=lockfile)

    with pytest.raises(
        NotImplementedError, match="mypy is only an optional dependency"
    ):
        current_versions_poetry({"mypy"}, set(), lockfile=lockfile)


def test_current_package_versions_uninstallable():
    env = Path(__file__).parent / "env-for-parsing-poetry-path-dep"
    with open(env / "poetry.lock", "rb") as f:
        lockfile = f.read()

    # Error regardless of whether it's required
    with pytest.raises(
        NotImplementedError, match="'sneks-sync' is installed as a path dependency"
    ):
        current_versions_poetry({"sneks-sync"}, set(), lockfile=lockfile)

    with pytest.raises(
        NotImplementedError, match="'sneks-sync' is installed as a path dependency"
    ):
        current_versions_poetry(set(), set(), lockfile=lockfile)
