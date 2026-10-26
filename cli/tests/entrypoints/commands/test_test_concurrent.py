"""`cstudy test` output for concurrent problems (docs/specs/cli.md#concurrent-problems)."""

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.concurrency_fakes import duplicating, queue, stalling
from tests.fakes import (
    Answer,
    FakeLanguageRunner,
    FakeStubGenerator,
    FakeToolchains,
    ScriptedRunnerProcess,
    make_environment,
    repository_root,
)
from tests.helpers import CONCURRENCY_PROBLEMS

runner = CliRunner()
TIMING = re.compile(r"\d+(\.\d+)?(ms|s)")
TIMES = "\N{MULTIPLICATION SIGN}"


def environment_for(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answer: Answer) -> None:
    toolchains = FakeToolchains(
        {Language.PYTHON: FakeLanguageRunner()}, {Language.PYTHON: FakeStubGenerator()}
    )
    environment = make_environment(
        repository_root(tmp_path, CONCURRENCY_PROBLEMS),
        toolchains=toolchains,
        runner_process=ScriptedRunnerProcess(answer),
    )
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    start_attempt(environment, StartRequest("bounded-blocking-queue", Language.PYTHON))


def lines(*arguments: str) -> list[str]:
    result = runner.invoke(cli.app, ["test", *arguments])
    return [TIMING.sub("T", line) for line in result.output.splitlines()]


def test_a_passing_run_lists_every_stress_case(tmp_path, monkeypatch):
    environment_for(tmp_path, monkeypatch, queue)
    assert lines() == [
        "bounded-blocking-queue · python · 6 sequential (2 visible, 4 hidden) · "
        f"2 stress {TIMES} 1 variant {TIMES} 3 runs",
        "",
        "PASS     ex1   T",
        "PASS     ex2   T",
        "PASS     4 hidden cases",
        "PASS     s1    thread · 3/3 runs · median T",
        "PASS     s2    thread · 3/3 runs · median T",
        "",
        "8/8 passed · total T",
        "stress runs found no race (not a proof of thread safety)",
        "all passed. Next: cstudy done --rating easy|ok|hard",
    ]


def test_a_failing_stress_case_lists_its_failing_runs(tmp_path, monkeypatch):
    environment_for(tmp_path, monkeypatch, duplicating)
    output = lines("--case", "s1", "--stress", "2")
    assert output[2:5] == [
        "FAIL     s1    thread · 0/2 runs passed",
        "               run 0 · seed 1000  equal_multisets put.arg0 vs take: "
        "1 missing (1000000), 1 extra (0)",
        "                         distinct take: 0 (2 times)",
    ]


def test_a_stall_names_the_deadline_and_the_waiting_workers(tmp_path, monkeypatch):
    environment_for(tmp_path, monkeypatch, stalling)
    output = lines("--case", "s2", "--stress", "1", "--seed", "7")
    assert output[2:4] == [
        "STALLED  s2    thread · 0/1 runs passed · deadline T",
        "               run 0 · seed 7  producer[0] in put (op 0 of 400)",
    ]


def test_stalled_runs_are_counted_in_the_summary(tmp_path, monkeypatch):
    environment_for(tmp_path, monkeypatch, stalling)
    assert lines("--case", "s2", "--stress", "1")[-1] == "0/1 passed · 1 stalled · total T"


def test_a_failing_stress_case_exits_1(tmp_path, monkeypatch):
    environment_for(tmp_path, monkeypatch, duplicating)
    result = runner.invoke(cli.app, ["test", "--case", "s1", "--stress", "1"])
    assert result.exit_code == ExitCode.FAILURES


def test_stress_runs_are_limited_to_100(tmp_path, monkeypatch):
    environment_for(tmp_path, monkeypatch, queue)
    result = runner.invoke(cli.app, ["test", "--stress", "101"])
    assert result.exit_code == ExitCode.USAGE_ERROR
