"""The Python project every workspace starts with (`cstudy test --debug` attaches through debugpy,
docs/specs/runners.md#debug-mode)."""

import tomllib

import pytest

from tests.helpers import WORKSPACE_TEMPLATE

PYTHON_TEMPLATE = WORKSPACE_TEMPLATE / "python"


@pytest.fixture(scope="module")
def project() -> dict:
    return tomllib.loads((PYTHON_TEMPLATE / "pyproject.toml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def locked_names() -> set[str]:
    lock = tomllib.loads((PYTHON_TEMPLATE / "uv.lock").read_text(encoding="utf-8"))
    return {package["name"] for package in lock["package"]}


def test_the_project_depends_on_debugpy_for_debugging(project):
    declared = [requirement.split(">")[0] for requirement in project["dependency-groups"]["dev"]]
    assert "debugpy" in declared


def test_debugpy_is_not_a_dependency_of_running_solutions(project):
    assert project["project"]["dependencies"] == ["cs-support"]


def test_the_lock_pins_debugpy(locked_names):
    assert "debugpy" in locked_names
