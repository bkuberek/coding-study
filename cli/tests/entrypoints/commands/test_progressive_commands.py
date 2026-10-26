"""`cstudy start` and `cstudy test` output for a progressive problem."""

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import start
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.e2e import e2e_environment
from tests.fakes import repository_root

runner = CliRunner()
PHASE4 = Path(__file__).resolve().parents[2] / "fixtures" / "phase4" / "problems"
REFERENCE = PHASE4 / "0001-level-store" / "solutions" / "hash-map.py"
STUB = "python/practice/level_store.py"
STATEMENT = ".statements/level-store.md"
TIMING = re.compile(r"\d+(\.\d+)?(ms|s)")


@pytest.fixture
def environment(tmp_path, monkeypatch):
    environment = e2e_environment(repository_root(tmp_path, PHASE4))
    monkeypatch.setattr(start, "load_environment", lambda *_: environment)
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    return environment


@pytest.fixture
def started(environment):
    runner.invoke(cli.app, ["start", "level-store", "--no-open"])
    return environment


def solve(environment) -> None:
    environment.workspace.write_text(STUB, REFERENCE.read_text())


def cs_test(*arguments: str):
    return runner.invoke(cli.app, ["test", *arguments])


def lines(result) -> list[str]:
    """Output lines with timings replaced by `T`."""
    return [TIMING.sub("T", line) for line in result.output.splitlines()]


def test_start_names_the_unlocked_level(environment):
    result = runner.invoke(cli.app, ["start", "level-store", "--no-open"])
    assert lines(result) == [
        "level-store · medium · practical · python",
        f"stub       {STUB}",
        f"statement  {STATEMENT}",
        "level      1 of 3: Put and get",
        "next       cstudy test --watch",
    ]


def test_passing_a_level_reports_the_unlocked_one(started):
    solve(started)
    assert lines(cs_test()) == [
        "level-store · python · level 1 of 3 · 4 cases (1 visible, 3 hidden, 0 generated)",
        "",
        "PASS     ex1   T",
        "PASS     3 hidden cases",
        "",
        "4/4 passed · total T",
        "level 1 passed · unlocked level 2 of 3: Remove and size",
        f"statement  {STATEMENT} (updated)",
    ]


def test_passing_a_level_exits_0(started):
    solve(started)
    assert cs_test().exit_code == ExitCode.SUCCESS


def test_later_runs_cover_every_unlocked_level(started):
    solve(started)
    cs_test()
    assert lines(cs_test())[0] == (
        "level-store · python · levels 1-2 of 3 · 8 cases (2 visible, 6 hidden, 0 generated)"
    )


def test_passing_the_last_level_points_to_cs_done(started):
    solve(started)
    cs_test()
    cs_test()
    assert lines(cs_test())[-1] == "all passed. Next: cstudy done --rating easy|ok|hard"


def test_level_runs_only_the_requested_levels(started):
    solve(started)
    cs_test()
    assert lines(cs_test("--level", "1"))[0].startswith(
        "level-store · python · level 1 of 3 · 4 cases"
    )


def test_passing_a_lower_level_unlocks_nothing(started):
    solve(started)
    cs_test()
    assert lines(cs_test("--level", "1"))[-1] == "all selected cases passed"


def test_a_locked_level_is_a_usage_error(started):
    result = cs_test("--level", "2")
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: level 2 is locked; pass level 1 with cstudy test first\n",
    )


def test_a_failing_level_reports_no_unlock(started):
    assert lines(cs_test())[-1] == "0/4 passed · 4 errors · total T"
