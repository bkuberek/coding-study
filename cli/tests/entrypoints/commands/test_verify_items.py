from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import verify
from coding_study.entrypoints.shared import ExitCode
from tests.e2e import e2e_environment
from tests.fakes import repository_root
from tests.helpers import FIXTURE_RUBRIC_PROBLEMS

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"


@pytest.fixture
def environment(tmp_path, monkeypatch):
    environment = e2e_environment(repository_root(tmp_path, PRACTICE, FIXTURE_RUBRIC_PROBLEMS))
    monkeypatch.setattr(verify, "load_environment", lambda *_: environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["verify", *arguments])


def test_track_report(environment):
    assert invoke("--track", "system-design", "--require-ready").output.splitlines() == [
        "news-feed         static ok · not ready",
        "  not ready: status is draft, not ready",
        "  not ready: system-design problems need at least one reference (links or study_guides)",
        "url-shortener     static ok",
        "",
        "coverage  python 0/0 · typescript 0/0 · java 0/0 · kotlin 0/0 · go 0/0 · rust 0/0",
        "result    1 failed · 1 passed",
    ]


def test_ready_rubric_problems_exit_0(environment):
    assert invoke("url-shortener", "retry-wrapper", "--require-ready").exit_code == 0


def test_static_rubric_problem_failure_exits_5(environment):
    (environment.root / "problems/retry-wrapper/change.diff").unlink()
    assert invoke("retry-wrapper").exit_code == ExitCode.CONTENT_ERROR
