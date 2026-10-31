"""`cstudy test --events` and `cstudy submit --events` through the real Python runner and pytest,
on the fixture project and on the pilot (docs/specs/cli.md#event-stream).

Each project is played from its starter, through a module that does not compile, to its reference.
The workspace's interpreter is a shim, as in test_project_end_to_end: the CLI's own Python, which
has pytest, with runners/python/src on its path.
"""

import json
import shutil
import sys
from pathlib import Path

import pytest
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
runner = CliRunner()


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
