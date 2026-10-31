"""`cstudy test --events` through the real runners on a problem of every kind that is not a
project: function, design, progressive, concurrent and the debugging track in Python, and a
function in Go (docs/specs/cli.md#event-stream).

Each problem is started in a copy of the session's practice workspace and played from a starting
file to its reference. A slow solution shows that each case is written as it ends, while the run
goes on: every line is timed as `typer.echo` writes it.
"""

import json
import shutil
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import typer
from jsonschema import Draft202012Validator
from typer.testing import CliRunner, Result

from coding_study.entrypoints import cli
from tests.helpers import CATALOG_PROBLEMS, REPOSITORY_ROOT, SCHEMAS_DIRECTORY
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

runner = CliRunner()
PROBLEMS = (
    "0001-two-sum",
    "0002-lru-cache",
    "0186-in-memory-database",
    "0201-bounded-blocking-queue",
    "0212-debug-recursion-base-case",
)
NO_GO = shutil.which("go") is None
VALIDATOR = Draft202012Validator(
    json.loads((SCHEMAS_DIRECTORY / "events.schema.json").read_text(encoding="utf-8"))
)
SLOW_CALL_SECONDS = 0.25
SLOW_TWO_SUM = f"""

import time as _time

_two_sum = two_sum


def two_sum(nums, target):
    _time.sleep({SLOW_CALL_SECONDS})
    return _two_sum(nums, target)
"""
BROKEN_GO = "package two_sum\n\nfunc twoSum(nums []int, target int) []int {\n\treturn missing\n}\n"
GO_USER_FILE = "go/practice/two_sum/two_sum.go"
SOLVED = (
    ("design solved", "lru-cache", "0002-lru-cache", "hash-map-dll.py"),
    ("progressive solved", "in-memory-database", "0186-in-memory-database", "versioned-fields.py"),
    ("concurrent solved", "bounded-blocking-queue", "0201-bounded-blocking-queue", "monitor.py"),
)
"""Each step that plays a problem's Python reference: its slug, directory and reference file."""


class TimedLines:
    """Stands in for `typer.echo`: keeps each event line with the time it was written."""

    def __init__(self, echo: Callable[..., None]) -> None:
        self._echo = echo
        self.lines: list[tuple[float, dict[str, Any]]] = []

    def __call__(self, message: Any = None, **options: Any) -> None:
        if isinstance(message, str) and message.startswith("{"):
            self.lines.append((time.monotonic(), json.loads(message)))
        self._echo(message, **options)

    def written_at(self, event_type: str) -> float:
        return next(at for at, event in self.lines if event["type"] == event_type)


class Practice:
    """`cstudy` in a workspace of its own, over a content root holding `PROBLEMS`."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def start(self, slug: str, language: str = "python") -> None:
        result = cs("start", slug, "--lang", language, "--no-open")
        assert result.exit_code == 0, result.output

    def write(self, path: str, text: str) -> None:
        (self.root / path).write_text(text, encoding="utf-8")

    def reference(self, problem: str, name: str) -> str:
        return (CATALOG_PROBLEMS / problem / "solutions" / name).read_text(encoding="utf-8")

    def timed(self, *arguments: str) -> TimedLines:
        lines = TimedLines(typer.echo)
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(typer, "echo", lines)
            cs("test", *arguments, "--events")
        return lines


def cs(*arguments: str) -> Result:
    return runner.invoke(cli.app, list(arguments))


def events(*arguments: str) -> list[dict]:
    return [json.loads(line) for line in cs("test", *arguments, "--events").stdout.splitlines()]


@pytest.fixture(scope="module")
def practice(
    tmp_path_factory: pytest.TempPathFactory, practice_workspace: Path
) -> Iterator[Practice]:
    content = tmp_path_factory.mktemp("events-content")
    shutil.copytree(SCHEMAS_DIRECTORY, content / "schemas")
    for problem in PROBLEMS:
        shutil.copytree(CATALOG_PROBLEMS / problem, content / "problems" / problem)
    (content / "runners").symlink_to(REPOSITORY_ROOT / "runners", target_is_directory=True)
    root = workspace_like(practice_workspace, tmp_path_factory.mktemp("events") / "ws")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CSTUDY_CONTENT", str(content))
        patch.setenv("CSTUDY_WORKSPACE", str(root))
        patch.setenv("CSTUDY_CONFIG", str(content / "absent-config.toml"))
        yield Practice(root)


@pytest.fixture(scope="module")
def played(practice: Practice) -> dict[str, list[dict]]:
    """Every stream, by step."""
    steps: dict[str, list[dict]] = {}
    practice.start("two-sum")
    steps["function stub"] = events("two-sum")
    practice.write("python/practice/two_sum.py", practice.reference("0001-two-sum", "hash-map.py"))
    steps["function solved"] = events("two-sum")
    for step, slug, problem, reference in SOLVED:
        practice.start(slug)
        user_file = f"python/practice/{slug.replace('-', '_')}.py"
        practice.write(user_file, practice.reference(problem, reference))
        steps[step] = events(slug)
    practice.start("debug-recursion-base-case")
    steps["debugging buggy"] = events("debug-recursion-base-case")
    reference = practice.reference("0212-debug-recursion-base-case", "leaf-base-case.py")
    practice.write("python/practice/debug_recursion_base_case.py", reference)
    steps["debugging fixed"] = events("debug-recursion-base-case")
    return steps


@pytest.fixture(scope="module")
def go(practice: Practice) -> dict[str, list[dict]]:
    if NO_GO:
        pytest.skip("go is not installed")
    practice.start("two-sum", "go")
    practice.write(GO_USER_FILE, BROKEN_GO)
    steps = {"broken": events("two-sum", "--lang", "go")}
    practice.write(GO_USER_FILE, practice.reference("0001-two-sum", "hash-map.go"))
    steps["solved"] = events("two-sum", "--lang", "go")
    return steps


@pytest.fixture(scope="module")
def slow(practice: Practice, played: dict[str, list[dict]]) -> TimedLines:
    """After `played`, which needs the stub."""
    solution = practice.reference("0001-two-sum", "hash-map.py") + SLOW_TWO_SUM
    practice.write("python/practice/two_sum.py", solution)
    return practice.timed("two-sum", "--lang", "python")


def of_type(found: list[dict], event_type: str) -> list[dict]:
    return [event for event in found if event["type"] == event_type]


def outcome(found: list[dict]) -> tuple[str, int]:
    end = found[-1]
    return end["outcome"], end["exit_code"]


STEPS = (
    "function stub",
    "function solved",
    "design solved",
    "progressive solved",
    "concurrent solved",
    "debugging buggy",
    "debugging fixed",
)


@pytest.mark.parametrize("step", STEPS)
def test_every_event_matches_the_schema(played, step):
    assert [event for event in played[step] if not VALIDATOR.is_valid(event)] == []


@pytest.mark.parametrize("step", STEPS)
def test_every_stream_runs_from_its_start_to_its_end(played, step):
    found = [event["type"] for event in played[step]]
    assert (found[0], found[-1]) == ("run_start", "run_end")


def test_the_stub_fails_every_case(played):
    assert {event["status"] for event in of_type(played["function stub"], "case_result")} == {
        "error"
    }


def test_the_function_reference_passes(played):
    assert outcome(played["function solved"]) == ("passed", 0)


def test_each_case_of_the_planned_count_starts_and_ends(played):
    found = played["function solved"]
    planned = found[0]["planned"]["cases"]
    started, ended = of_type(found, "case_start"), of_type(found, "case_result")
    assert (len(started), len(ended)) == (planned, planned)


def test_the_design_reference_passes(played):
    found = played["design solved"]
    assert (found[0]["kind"], outcome(found)) == ("design", ("passed", 0))


def test_the_progressive_reference_opens_level_2(played):
    (opened,) = of_type(played["progressive solved"], "level_unlocked")
    assert (opened["level"], opened["tests"]) == (2, None)


def test_the_concurrent_reference_passes_every_stress_run(played):
    found = played["concurrent solved"]
    statuses = {event["status"] for event in of_type(found, "stress_run")}
    assert (statuses, outcome(found)) == ({"pass"}, ("passed", 0))


def test_each_planned_stress_run_is_reported(played):
    found = played["concurrent solved"]
    stress = found[0]["planned"]["stress"]
    planned = stress["cases"] * stress["variants"] * stress["runs"]
    assert len(of_type(found, "stress_run")) == planned


def test_each_stress_case_and_variant_is_graded(played):
    found = played["concurrent solved"]
    stress = found[0]["planned"]["stress"]
    assert len(of_type(found, "stress_result")) == stress["cases"] * stress["variants"]


def test_the_buggy_starter_fails(played):
    found = played["debugging buggy"]
    assert (found[0]["track"], outcome(found)) == ("debugging", ("failed", 1))


def test_the_fixed_debugging_problem_passes(played):
    assert outcome(played["debugging fixed"]) == ("passed", 0)


def test_go_that_does_not_build_is_a_build_and_a_diagnostic(go):
    found = go["broken"]
    (build,) = of_type(found, "build")
    diagnostics = of_type(found, "diagnostic")
    assert (build["note"], diagnostics[0]["source"], outcome(found)) == (
        None,
        "build",
        ("build_failed", 2),
    )


def test_go_that_does_not_build_is_a_diagnostic_at_the_users_file_and_line(go):
    diagnostic = of_type(go["broken"], "diagnostic")[0]
    assert (diagnostic["file"], diagnostic["line"], diagnostic["message"]) == (
        GO_USER_FILE,
        4,
        "undefined: missing",
    )


def test_go_that_builds_names_its_build_before_its_cases(go):
    found = [event["type"] for event in go["solved"]]
    assert found.index("build") < found.index("case_start")


def test_the_go_reference_reports_each_case_live_and_passes(go):
    found = go["solved"]
    planned = found[0]["planned"]["cases"]
    assert (len(of_type(found, "case_result")), outcome(found)) == (planned, ("passed", 0))


@pytest.mark.parametrize("step", ["broken", "solved"])
def test_every_go_event_matches_the_schema(go, step):
    assert [event for event in go[step] if not VALIDATOR.is_valid(event)] == []


def test_the_first_result_is_written_while_the_other_cases_still_run(slow):
    written_before_the_end = slow.written_at("run_end") - slow.written_at("case_result")
    assert written_before_the_end >= SLOW_CALL_SECONDS * 0.8


def test_a_slow_cases_result_follows_its_start_by_its_duration(slow):
    ran_for = slow.written_at("case_result") - slow.written_at("case_start")
    assert ran_for >= SLOW_CALL_SECONDS * 0.8
