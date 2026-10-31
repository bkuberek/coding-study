"""Launching the Python runner for project jobs (docs/specs/runners.md#launch)."""

from collections.abc import Sequence
from pathlib import Path

import pytest

from coding_study.adapters.languages.python.runner import (
    DEBUG_BOOTSTRAP,
    READY_MARKER,
    PythonRunner,
)
from coding_study.application.ports import (
    ProbeResult,
    ProjectGrading,
    ProjectRunner,
    ProjectScope,
    ProjectSuite,
    RunnerLaunch,
)
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.problem import Language
from coding_study.domain.runs import HELLO_TIMEOUT_MS
from coding_study.domain.workspace_projects import PYTEST_INSTALL_COMMAND

INTERPRETER = Path("python/.venv/bin/python")
PYTEST_PACKAGE = Path("python/.venv/lib/python3.13/site-packages/pytest/__init__.py")
PROJECT = Path("projects/bank-project-python")
SESSION = DebugSession(Language.PYTHON, 5678)
IMPORTABLE = ProbeResult(0, "")


class FakeProbe:
    def __init__(self, result: ProbeResult | None = IMPORTABLE) -> None:
        self.result = result

    def run(self, command: Sequence[str]) -> ProbeResult | None:
        return self.result


@pytest.fixture
def root(tmp_path: Path) -> Path:
    for installed in (INTERPRETER, PYTEST_PACKAGE):
        (tmp_path / installed).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / installed).touch()
    return tmp_path


def prepare(root: Path, scope: ProjectScope, probe: FakeProbe | None = None) -> RunnerLaunch:
    return PythonRunner(root, probe or FakeProbe()).prepare_project(scope, [].append)


def test_the_python_runner_runs_project_jobs(root):
    assert isinstance(PythonRunner(root), ProjectRunner)


def test_a_grading_job_runs_the_runner_module_without_the_working_directory_on_the_path(root):
    launch = prepare(root, ProjectGrading(root / PROJECT))
    assert launch.command == (str(root / INTERPRETER), "-P", "-m", "cs_runner")


def test_a_project_job_starts_in_the_project_root(root):
    assert prepare(root, ProjectGrading(root / PROJECT)).cwd == root / PROJECT


def test_a_project_job_keeps_bytecode_in_the_workspace_and_uv_from_syncing(root):
    assert prepare(root, ProjectGrading(root / PROJECT)).environment == {
        "UV_NO_SYNC": "1",
        "PYTHONPYCACHEPREFIX": str(root / ".cs/pycache"),
    }


def test_a_project_job_gets_the_python_hello_timeout(root):
    launch = prepare(root, ProjectGrading(root / PROJECT))
    assert launch.hello_timeout_ms == HELLO_TIMEOUT_MS[Language.PYTHON]


def test_a_suite_job_launches_like_a_grading_job(root):
    suite = prepare(root, ProjectSuite(root / PROJECT))
    assert suite == prepare(root, ProjectGrading(root / PROJECT))


def test_a_suite_job_needs_pytest_in_the_workspace_environment(root):
    (root / PYTEST_PACKAGE).unlink()
    with pytest.raises(RunnerStartError, match=PYTEST_INSTALL_COMMAND):
        prepare(root, ProjectSuite(root / PROJECT))


def test_a_grading_job_does_not_need_pytest(root):
    (root / PYTEST_PACKAGE).unlink()
    assert prepare(root, ProjectGrading(root / PROJECT)).cwd == root / PROJECT


def test_a_project_job_needs_the_workspace_environment(tmp_path):
    with pytest.raises(RunnerStartError, match="uv sync"):
        prepare(tmp_path, ProjectGrading(tmp_path / PROJECT))


def test_a_debugged_suite_runs_the_bootstrap_without_the_working_directory_on_the_path(root):
    launch = prepare(root, ProjectSuite(root / PROJECT, SESSION))
    assert launch.command == (
        str(root / INTERPRETER),
        "-P",
        "-X",
        "frozen_modules=off",
        "-c",
        DEBUG_BOOTSTRAP,
        "5678",
    )


def test_a_debugged_suite_waits_for_the_ready_marker(root):
    debug = prepare(root, ProjectSuite(root / PROJECT, SESSION)).debug
    assert debug is not None
    assert debug.ready_marker == READY_MARKER


def test_a_debugged_suite_keeps_the_project_environment(root):
    launch = prepare(root, ProjectSuite(root / PROJECT, SESSION))
    assert (launch.cwd, launch.environment["UV_NO_SYNC"]) == (root / PROJECT, "1")


def test_a_debugged_suite_needs_debugpy(root):
    with pytest.raises(RunnerStartError, match="debugpy"):
        prepare(root, ProjectSuite(root / PROJECT, SESSION), FakeProbe(ProbeResult(1, "")))


def bytecode_of(root: Path, project: Path) -> Path:
    """Where `PYTHONPYCACHEPREFIX` mirrors the project's absolute path."""
    return root / ".cs/pycache" / project.resolve().relative_to(project.resolve().anchor)


def cached(directory: Path) -> Path:
    stale = directory / "bank" / "__pycache__" / "bank.cpython-313.pyc"
    stale.parent.mkdir(parents=True)
    stale.touch()
    return stale


@pytest.mark.parametrize("scope", [ProjectGrading, ProjectSuite])
def test_a_project_job_starts_without_the_projects_stale_bytecode(root, scope):
    stale = cached(bytecode_of(root, root / PROJECT))
    prepare(root, scope(root / PROJECT))
    assert not stale.exists()


def test_a_project_job_keeps_the_bytecode_of_other_projects(root):
    other = cached(bytecode_of(root, root / "projects/other"))
    prepare(root, ProjectGrading(root / PROJECT))
    assert other.exists()


def test_a_project_job_keeps_the_bytecode_of_the_shared_environment(root):
    library = cached(bytecode_of(root, root / "python/.venv/lib"))
    prepare(root, ProjectGrading(root / PROJECT))
    assert library.exists()


def test_a_project_job_clears_the_bytecode_of_a_project_reached_through_a_link(root):
    (root / PROJECT).parent.mkdir(parents=True)
    real = root / "elsewhere"
    real.mkdir()
    (root / PROJECT).symlink_to(real)
    stale = cached(bytecode_of(root, real))
    prepare(root, ProjectGrading(root / PROJECT))
    assert not stale.exists()
