"""Playing the pilot project problem from `cstudy start` to `cstudy done` through the real Python
runner and pytest (docs/specs/cli.md#cstudy-submit).

The workspace is a temporary directory whose interpreter is a shim: the CLI's own Python, which
has pytest, with runners/python/src on its path, so the test does not depend on `uv sync` having
run in a workspace. The pilot is `draft`; `cstudy start` plays a draft like any other problem.
"""

import shutil
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from coding_study.adapters.languages.python.runner import PythonRunner
from coding_study.adapters.languages.python.test_generator import PythonTestGenerator
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.environment import Environment
from coding_study.domain.attempts import AttemptStatus
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import done, start, status, submit
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import CATALOG_PROBLEMS, REPOSITORY_ROOT

pytestmark = pytest.mark.slow

SLUG = "bank-project-python"
PILOT = CATALOG_PROBLEMS / "0249-bank-project-python"
RUNNER_SOURCES = REPOSITORY_ROOT / "runners" / "python" / "src"
PYTEST_MARKER = Path("python/.venv/lib/python3.13/site-packages/pytest/__init__.py")
FOLDER = Path("projects") / SLUG
COMMANDS = (start, test_command, submit, status, done)
runner = CliRunner()


@pytest.fixture(scope="module")
def environment(tmp_path_factory: pytest.TempPathFactory) -> Environment:
    catalog = tmp_path_factory.mktemp("catalog")
    shutil.copytree(PILOT, catalog / PILOT.name)
    root = repository_root(tmp_path_factory.mktemp("workspace"), catalog)
    interpreter = root / "python" / ".venv" / "bin" / "python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text(
        f'#!/bin/sh\nPYTHONPATH="{RUNNER_SOURCES}" exec "{sys.executable}" "$@"\n'
    )
    interpreter.chmod(0o755)
    (root / PYTEST_MARKER).parent.mkdir(parents=True)
    (root / PYTEST_MARKER).touch()
    toolchains = FakeToolchains(
        runners={Language.PYTHON: PythonRunner(root)},
        project_test_generators={Language.PYTHON: PythonTestGenerator()},
    )
    runs = SubprocessRunner(root / ".cs" / "runs")
    return make_environment(root, toolchains=toolchains, runner_process=runs)


@pytest.fixture(scope="module")
def cstudy(environment: Environment) -> Iterator[None]:
    with pytest.MonkeyPatch.context() as patch:
        for command in COMMANDS:
            patch.setattr(command, "load_environment", lambda *_: environment)
        yield


def cs(*arguments: str) -> Result:
    return runner.invoke(cli.app, list(arguments))


@pytest.fixture(scope="module")
def played(environment: Environment, cstudy: None) -> dict[str, Result]:
    """Every step of one play-through, in order."""
    steps = {"start": cs("start", SLUG, "--no-open"), "bare test": cs("test")}
    shutil.copytree(
        PILOT / "solutions" / "reference", environment.root / FOLDER, dirs_exist_ok=True
    )
    steps["solved test"] = cs("test")
    for level in (2, 3, 4):
        steps[f"submit for level {level}"] = cs("submit")
    steps["last submit"] = cs("submit")
    steps["status"] = cs("status")
    steps["done"] = cs("done", "--rating", "ok")
    return steps


def test_start_writes_the_folder(environment, played):
    assert (environment.root / FOLDER / "bank" / "bank.py").is_file()


def test_start_writes_level_1s_tests(environment, played):
    assert (environment.root / FOLDER / "tests" / "test_level_1.py").is_file()


def test_start_names_level_1(played):
    assert "level      1 of 4: Accounts and transfers" in played["start"].output


def test_the_bare_starter_fails_both_generated_tests(played):
    assert played["bare test"].output.splitlines()[-1].startswith("0/2 passed")


def test_the_bare_starter_exits_1(played):
    assert played["bare test"].exit_code == ExitCode.FAILURES


def test_the_reference_passes_the_suite(played):
    assert played["solved test"].output.splitlines()[-1] == "all passed. Next: cstudy submit"


@pytest.mark.parametrize("level", [2, 3, 4])
def test_each_submission_unlocks_the_next_level(played, level):
    assert f"level {level} unlocked: " in played[f"submit for level {level}"].output


@pytest.mark.parametrize("level", [2, 3, 4])
def test_each_opened_level_gets_its_test_file(environment, played, level):
    assert (environment.root / FOLDER / "tests" / f"test_level_{level}.py").is_file()


def test_the_last_submission_finishes_every_level(played):
    assert played["last submit"].output.splitlines()[-1] == (
        "all passed · every level done. Next: cstudy done --rating easy|ok|hard"
    )


def test_status_shows_every_level_open(played):
    assert "level      4 of 4: Merges and balance history" in played["status"].output


def test_status_points_to_done(played):
    assert played["status"].output.splitlines()[-1] == (
        "next       cstudy done --rating easy|ok|hard"
    )


def test_done_records_a_passed_attempt_with_every_level(played):
    assert " · passed · levels 4 of 4 · " in played["done"].output


def test_done_finishes_the_attempt(environment, played):
    attempt = environment.progress.latest_attempt(SLUG, Language.PYTHON)
    assert getattr(attempt, "status", None) is AttemptStatus.PASSED
