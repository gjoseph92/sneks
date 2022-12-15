from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import tomli
from importlib_metadata import version

from sneks.parse_pdm import current_versions_pdm

env = Path(__file__).parent / "env-for-parsing-pdm"


@pytest.fixture(scope="module")
def pyproject() -> dict[str, Any]:
    with open(env / "pyproject.toml", "rb") as f:
        return tomli.load(f)


@pytest.fixture(scope="module")
def lockfile() -> dict[str, Any]:
    with open(env / "pdm.lock", "rb") as f:
        return tomli.load(f)


def test_all_required(pyproject, lockfile):
    reqs, overrides = current_versions_pdm(
        {"dask", "distributed", "yapf"}, set(), lockfile, pyproject
    )
    assert set(reqs) == {
        "dask==2022.5.2",
        "distributed==2022.5.2",
        "git+https://github.com/google/yapf.git@c6077954245bc3add82dafd853a1c7305a6ebd20",
    }
    assert not overrides


def test_optional_included(pyproject, lockfile):
    reqs, overrides = current_versions_pdm(
        {"dask", "distributed"}, {"yapf"}, lockfile, pyproject
    )
    assert set(reqs) == {
        "dask==2022.5.2",
        "distributed==2022.5.2",
        "git+https://github.com/google/yapf.git@c6077954245bc3add82dafd853a1c7305a6ebd20",
    }
    assert not overrides


def test_missing_optional_ignored(pyproject, lockfile):
    reqs, overrides = current_versions_pdm(
        {"dask", "distributed"}, {"bokeh", "foo"}, lockfile, pyproject
    )
    assert set(reqs) == {
        "dask==2022.5.2",
        "distributed==2022.5.2",
        "bokeh==2.4.3",
    }
    assert not overrides


def test_override(pyproject, lockfile):
    reqs, overrides = current_versions_pdm(
        {"distributed"}, {"psutil"}, lockfile, pyproject
    )
    assert set(reqs) == {"distributed==2022.5.2"}
    assert set(overrides) == {"psutil==4.4.2"}


def test_missing_required_raises(pyproject, lockfile):
    with pytest.raises(ValueError, match="pdm add blaze scipy"):
        current_versions_pdm({"blaze", "bokeh", "scipy"}, set(), lockfile, pyproject)


@pytest.mark.skip("not supported")
def test_required_is_dev(pyproject, lockfile):
    with pytest.raises(ValueError, match="flake8 is only a dev dependency"):
        current_versions_pdm({"flake8"}, set(), lockfile, pyproject)


@pytest.mark.skip("not supported")
def test_required_is_optional(pyproject, lockfile):
    with pytest.raises(
        NotImplementedError, match="mypy is only an optional dependency"
    ):
        current_versions_pdm({"mypy"}, set(), lockfile, pyproject)


def test_required_is_path_raises(pyproject, lockfile):
    with pytest.raises(
        NotImplementedError, match="'sneks-sync' is installed as a path dependency"
    ):
        current_versions_pdm({"sneks-sync"}, set(), lockfile, pyproject)


def test_optional_is_path_allowed(pyproject, lockfile):
    reqs, overrides = current_versions_pdm(
        {"distributed"}, {"sneks-sync"}, lockfile, pyproject
    )
    assert set(reqs) == {
        "distributed==2022.5.2",
        f"sneks-sync=={version('sneks-sync')}",
    }
    assert not overrides
