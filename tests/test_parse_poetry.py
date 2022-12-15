from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import tomli

from sneks.parse_poetry import current_versions_poetry

env = Path(__file__).parent / "env-for-parsing-poetry"


@pytest.fixture(scope="module")
def pyproject() -> dict[str, Any]:
    with open(env / "pyproject.toml", "rb") as f:
        return tomli.load(f)


@pytest.fixture(scope="module")
def lockfile() -> dict[str, Any]:
    with open(env / "poetry.lock", "rb") as f:
        return tomli.load(f)


def test_all_required(pyproject, lockfile):
    reqs, overrides = current_versions_poetry(
        {"dask", "distributed", "yapf"}, set(), lockfile, pyproject
    )
    assert set(reqs) == {
        "dask==2022.5.2",
        "distributed==2022.5.2",
        "git+https://github.com/google/yapf.git@c6077954245bc3add82dafd853a1c7305a6ebd20",
    }
    assert not overrides


def test_optional_included(pyproject, lockfile):
    reqs, overrides = current_versions_poetry(
        {"dask", "distributed"}, {"yapf"}, lockfile, pyproject
    )
    assert set(reqs) == {
        "dask==2022.5.2",
        "distributed==2022.5.2",
        "git+https://github.com/google/yapf.git@c6077954245bc3add82dafd853a1c7305a6ebd20",
    }
    assert not overrides


def test_missing_optional_ignored(pyproject, lockfile):
    reqs, overrides = current_versions_poetry(
        {"dask", "distributed"}, {"bokeh", "foo"}, lockfile, pyproject
    )
    assert set(reqs) == {
        "dask==2022.5.2",
        "distributed==2022.5.2",
        "bokeh==2.4.3",
    }
    assert not overrides


def test_missing_required_raises(pyproject, lockfile):

    with pytest.raises(ValueError, match="poetry add blaze scipy"):
        current_versions_poetry({"blaze", "bokeh", "scipy"}, set(), lockfile, pyproject)


def test_required_is_dev(pyproject, lockfile):

    with pytest.raises(ValueError, match="flake8 is only a dev dependency"):
        current_versions_poetry({"flake8"}, set(), lockfile, pyproject)


def test_required_is_optional(pyproject, lockfile):

    with pytest.raises(
        NotImplementedError, match="mypy is only an optional dependency"
    ):
        current_versions_poetry({"mypy"}, set(), lockfile, pyproject)


def test_current_package_versions_uninstallable():
    env = Path(__file__).parent / "env-for-parsing-poetry-path-dep"
    with open(env / "pyproject.toml", "rb") as f:
        pyproject = tomli.load(f)
    with open(env / "poetry.lock", "rb") as f:
        lockfile = tomli.load(f)

    # Error regardless of whether it's required
    with pytest.raises(
        NotImplementedError, match="'sneks-sync' is installed as a path dependency"
    ):
        current_versions_poetry({"sneks-sync"}, set(), lockfile, pyproject)

    with pytest.raises(
        NotImplementedError, match="'sneks-sync' is installed as a path dependency"
    ):
        current_versions_poetry(set(), set(), lockfile, pyproject)
