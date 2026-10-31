"""`cstudy test --events` and `cstudy submit --events` through the real Python runner and pytest,
on the fixture project and on the pilot (docs/specs/cli.md#event-stream).

Each project is played from its starter, through a module that does not compile, to its reference.
Then the fixture project gets a slow test of its own and a slow method, to show that each test and
case is written as it starts, while the run goes on. The workspace's interpreter is a shim, as in
test_project_end_to_end: the CLI's own Python, which has pytest, with runners/python/src on its
path.
"""

import json
import shutil
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import typer
from jsonschema import Draft202012Validator
from typer.testing import CliRunner, Result

from coding_study.adapters.languages.python.runner import PythonRunner
from coding_study.adapters.languages.python.test_generator import PythonTestGenerator
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.environment import Environment
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import start, submit
from coding_study.entrypoints.commands import test as test_command
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import CATALOG_PROBLEMS, PROJECT_PROBLEMS, REPOSITORY_ROOT, SCHEMAS_DIRECTORY

pytestmark = pytest.mark.slow

SLUG = "bank-project-python"
PROJECTS = {
    "fixture": PROJECT_PROBLEMS / "0001-bank-project-python",
    "pilot": CATALOG_PROBLEMS / "0249-bank-project-python",
}
RUNNER_SOURCES = REPOSITORY_ROOT / "runners" / "python" / "src"
PYTEST_MARKER = Path("python/.venv/lib/python3.13/site-packages/pytest/__init__.py")
ENTRY_MODULE = Path("projects") / SLUG / "bank" / "bank.py"
BROKEN_LINE = 3
BROKEN_MODULE = "class Bank:\n    pass\n    def broken(:\n"
STREAMS = ("bare test", "broken test", "broken submit", "solved test", "solved submit")
COMMANDS = (start, test_command, submit)
VALIDATOR = Draft202012Validator(
    json.loads((SCHEMAS_DIRECTORY / "events.schema.json").read_text(encoding="utf-8"))
)
SLOW_TEST_SECONDS = 1.0
SLOW_TEST = f"""import time


def test_slow():
    time.sleep({SLOW_TEST_SECONDS})
"""
SLOW_TEST_ID = "tests/test_slow.py::test_slow"
SLOW_CALL_SECONDS = 0.25
SLOW_METHOD = f"""

import time as _time

_create_account = Bank.create_account


def _slow_create_account(self, timestamp, account_id):
    _time.sleep({SLOW_CALL_SECONDS})
    return _create_account(self, timestamp, account_id)


Bank.create_account = _slow_create_account
"""
runner = CliRunner()


class TimedLines:
    """Stands in for `typer.echo`: keeps each event line with the time it was written."""

    def __init__(self, echo: Callable[..., None]) -> None:
        self._echo = echo
        self.lines: list[tuple[float, dict[str, Any]]] = []

    def __call__(self, message: Any = None, **options: Any) -> None:
        if isinstance(message, str) and message.startswith("{"):
            self.lines.append((time.monotonic(), json.loads(message)))
        self._echo(message, **options)

    def written_at(self, event_type: str, event_id: str | None = None) -> float:
        return next(
            at
            for at, event in self.lines
            if event["type"] == event_type and event_id in (None, event.get("id"))
        )


def project_environment(root: Path, source: Path) -> Environment:
    """A workspace holding only `source`, whose Python is the shim."""
    catalog = root / "catalog"
    shutil.copytree(source, catalog / source.name)
    workspace = repository_root(root / "workspace", catalog)
    interpreter = workspace / "python" / ".venv" / "bin" / "python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text(
        f'#!/bin/sh\nPYTHONPATH="{RUNNER_SOURCES}" exec "{sys.executable}" "$@"\n'
    )
    interpreter.chmod(0o755)
    (workspace / PYTEST_MARKER).parent.mkdir(parents=True)
    (workspace / PYTEST_MARKER).touch()
    toolchains = FakeToolchains(
        runners={Language.PYTHON: PythonRunner(workspace)},
        project_test_generators={Language.PYTHON: PythonTestGenerator()},
    )
    runs = SubprocessRunner(workspace / ".cs" / "runs")
    return make_environment(workspace, toolchains=toolchains, runner_process=runs)


def cs(*arguments: str) -> Result:
    return runner.invoke(cli.app, list(arguments))


@pytest.fixture(scope="module", params=sorted(PROJECTS))
def played(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> dict[str, Result]:
    """Every stream of one play-through, by step."""
    source = PROJECTS[request.param]
    environment = project_environment(tmp_path_factory.mktemp(request.param), source)
    entry = environment.root / ENTRY_MODULE
    with pytest.MonkeyPatch.context() as patch:
        for command in COMMANDS:
            patch.setattr(command, "load_environment", lambda *_: environment)
        cs("start", SLUG, "--no-open")
        steps = {"bare test": cs("test", "--events")}
        starter = entry.read_text(encoding="utf-8")
        entry.write_text(BROKEN_MODULE, encoding="utf-8")
        steps["broken test"] = cs("test", "--events")
        steps["broken submit"] = cs("submit", "--events")
        entry.write_text(starter, encoding="utf-8")
        shutil.copytree(source / "solutions" / "reference", entry.parents[1], dirs_exist_ok=True)
        steps["solved test"] = cs("test", "--events")
        steps["solved submit"] = cs("submit", "--events")
    return steps


def events(result: Result) -> list[dict]:
    return [json.loads(line) for line in result.stdout.splitlines()]


def of_type(result: Result, event_type: str) -> list[dict]:
    return [event for event in events(result) if event["type"] == event_type]


@pytest.mark.parametrize("step", STREAMS)
def test_every_event_matches_the_schema(played, step):
    assert [event for event in events(played[step]) if not VALIDATOR.is_valid(event)] == []


@pytest.mark.parametrize("step", STREAMS)
def test_every_stream_runs_from_its_start_to_its_end(played, step):
    found = [event["type"] for event in events(played[step])]
    assert (found[0], found[-1]) == ("run_start", "run_end")


@pytest.mark.parametrize("step", STREAMS)
def test_every_stream_exits_as_its_end_says(played, step):
    result = played[step]
    assert result.exit_code == events(result)[-1]["exit_code"]


def test_the_bare_starter_fails_its_tests(played):
    assert events(played["bare test"])[-1]["outcome"] == "failed"


def test_the_bare_starters_tests_each_fail(played):
    statuses = {event["status"] for event in of_type(played["bare test"], "test_result")}
    assert statuses == {"error"}


@pytest.mark.parametrize("step", ["broken test", "broken submit"])
def test_a_module_that_does_not_compile_is_a_diagnostic_at_its_line(played, step):
    (diagnostic,) = of_type(played[step], "diagnostic")
    assert (diagnostic["file"], diagnostic["line"], diagnostic["code"]) == (
        "bank/bank.py",
        BROKEN_LINE,
        "SyntaxError",
    )


def test_a_submission_that_does_not_load_ends_load_failed(played):
    assert events(played["broken submit"])[-1]["outcome"] == "load_failed"


def test_the_reference_passes_its_tests(played):
    assert events(played["solved test"])[-1]["outcome"] == "passed"


def test_the_references_submission_grades_level_1(played):
    assert [event["level"] for event in of_type(played["solved submit"], "level_result")] == [1]


def test_the_references_submission_opens_level_2(played):
    (opened,) = of_type(played["solved submit"], "level_unlocked")
    assert (opened["level"], opened["tests"]["path"]) == (2, "tests/test_level_2.py")


@pytest.fixture(scope="module")
def timed(tmp_path_factory: pytest.TempPathFactory) -> dict[str, TimedLines]:
    """The fixture project's reference, with a slow test of its own and then a slow method, run
    with every event line timed as it is written."""
    source = PROJECTS["fixture"]
    environment = project_environment(tmp_path_factory.mktemp("timed"), source)
    entry = environment.root / ENTRY_MODULE
    runs: dict[str, TimedLines] = {}
    with pytest.MonkeyPatch.context() as patch:
        for command in COMMANDS:
            patch.setattr(command, "load_environment", lambda *_: environment)
        cs("start", SLUG, "--no-open")
        shutil.copytree(source / "solutions" / "reference", entry.parents[1], dirs_exist_ok=True)
        (entry.parents[1] / "tests" / "test_slow.py").write_text(SLOW_TEST, encoding="utf-8")
        for step, command in (("slow test", "test"), ("slow submit", "submit")):
            if command == "submit":
                entry.write_text(entry.read_text(encoding="utf-8") + SLOW_METHOD, encoding="utf-8")
            runs[step] = TimedLines(typer.echo)
            patch.setattr(typer, "echo", runs[step])
            cs(command, "--events")
            patch.setattr(typer, "echo", runs[step]._echo)
    return runs


def test_a_slow_tests_start_is_written_while_it_runs(timed):
    lines = timed["slow test"]
    started_before_the_end = lines.written_at("run_end") - lines.written_at(
        "test_start", SLOW_TEST_ID
    )
    assert started_before_the_end >= SLOW_TEST_SECONDS * 0.8


def test_a_slow_tests_result_follows_its_start_by_its_duration(timed):
    lines = timed["slow test"]
    ran_for = lines.written_at("test_result", SLOW_TEST_ID) - lines.written_at(
        "test_start", SLOW_TEST_ID
    )
    assert ran_for >= SLOW_TEST_SECONDS * 0.8


def test_the_first_graded_case_is_written_while_the_others_still_run(timed):
    lines = timed["slow submit"]
    graded_before_the_end = lines.written_at("run_end") - lines.written_at("case_result")
    assert graded_before_the_end >= SLOW_CALL_SECONDS * 0.8


def test_every_timed_line_matches_the_schema(timed):
    lines = [event for run in timed.values() for _, event in run.lines]
    assert [event for event in lines if not VALIDATOR.is_valid(event)] == []
