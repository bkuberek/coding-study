"""Grading the pilot project problem through the real Python runner
(docs/specs/runners.md#grading-job).

The workspace is a temporary directory whose interpreter is a shim: the CLI's own Python with
runners/python/src on its path, so the test does not depend on `uv sync` having run in a workspace.
"""

import shutil
import sys
from pathlib import Path

import pytest

from coding_study.adapters.languages.python.runner import PythonRunner
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.environment import Environment
from coding_study.application.project_runs import GradingRun, run_grading
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.judging import Judgement
from coding_study.domain.levels import cases_up_to
from coding_study.domain.problem import Language, Problem
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import CATALOG_PROBLEMS, REPOSITORY_ROOT

pytestmark = pytest.mark.slow

SLUG = "bank-project-python"
PILOT = CATALOG_PROBLEMS / "0249-bank-project-python"
RUNNER_SOURCES = REPOSITORY_ROOT / "runners" / "python" / "src"
LAST_LEVEL = 4
CASES_THROUGH_LAST_LEVEL = 28


@pytest.fixture(scope="module")
def workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    catalog = tmp_path_factory.mktemp("catalog")
    shutil.copytree(PILOT, catalog / PILOT.name)
    root = repository_root(tmp_path_factory.mktemp("workspace"), catalog)
    interpreter = root / "python" / ".venv" / "bin" / "python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text(
        f'#!/bin/sh\nPYTHONPATH="{RUNNER_SOURCES}" exec "{sys.executable}" "$@"\n'
    )
    interpreter.chmod(0o755)
    return root


@pytest.fixture(scope="module")
def environment(workspace: Path) -> Environment:
    return make_environment(
        workspace,
        toolchains=FakeToolchains(runners={Language.PYTHON: PythonRunner(workspace)}),
        runner_process=SubprocessRunner(workspace / ".cs" / "runs"),
    )


@pytest.fixture(scope="module")
def problem(environment: Environment) -> Problem:
    return environment.problems.load(SLUG)


def project_folder(workspace: Path, name: str, *trees: str) -> Path:
    """A new folder holding `starter/`, then each of the `solutions/<tree>` overlays on it."""
    folder = workspace / "projects" / name
    shutil.copytree(PILOT / "starter", folder)
    for tree in trees:
        shutil.copytree(PILOT / "solutions" / tree, folder, dirs_exist_ok=True)
    return folder


def grade(environment: Environment, problem: Problem, folder: Path, level: int) -> Judgement:
    run = GradingRun(problem, Language.PYTHON, folder, level)
    return run_grading(environment, run, print)


def test_the_pilots_reference_over_its_starter_passes_every_case_through_level_4(
    workspace, environment, problem
):
    folder = project_folder(workspace, "reference", "reference")
    judgement = grade(environment, problem, folder, LAST_LEVEL)
    assert (judgement.passed, judgement.case_count) == (True, CASES_THROUGH_LAST_LEVEL)


def test_the_bare_starter_fails_the_level_1_cases_with_errors(workspace, environment, problem):
    folder = project_folder(workspace, "starter")
    judgement = grade(environment, problem, folder, 1)
    level_1_cases = len(cases_up_to(problem.cases, 1))
    assert (judgement.load_error, judgement.count(CaseStatus.ERROR)) == (None, level_1_cases)
