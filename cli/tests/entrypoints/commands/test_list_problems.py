from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import ReviewState, ScheduleEntry
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import list_problems
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import NOW, make_environment, repository_root

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
HEADER = "ID    SLUG              DIFF    PATTERN          STATUS    DUE         REFS"


@pytest.fixture
def environment(tmp_path, monkeypatch):
    environment = make_environment(repository_root(tmp_path, PRACTICE))
    monkeypatch.setattr(list_problems, "load_catalog_environment", lambda *_: environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["list", *arguments])


def test_lists_every_problem(environment):
    assert invoke().output.splitlines() == [
        HEADER,
        "0001  two-sum           easy    arrays-hashing   new       -           py",
        "0002  lru-cache         medium  linked-list      new       -           py",
    ]


def test_exits_0(environment):
    assert invoke().exit_code == 0


def test_shows_progress_status_and_due_date(environment):
    attempt = environment.progress.add_attempt(
        NewAttempt("two-sum", Language.PYTHON, AttemptMode.NEW, NOW)
    )
    environment.progress.update_attempt(replace(attempt, status=AttemptStatus.PASSED))
    environment.progress.save_schedule_entry(
        ScheduleEntry("two-sum", ReviewState(interval_days=3), date(2026, 10, 27), Grade.OK, NOW)
    )
    row = invoke().output.splitlines()[1]
    assert row == "0001  two-sum           easy    arrays-hashing   passed    2026-10-27  py"


def test_long_slugs_and_patterns_are_truncated(environment):
    meta = environment.root / "problems/0002-lru-cache/meta.yaml"
    meta.write_text(meta.read_text().replace("[linked-list]", "[segment-tree-fenwick]"))
    directory = environment.root / "problems/0002-lru-cache"
    renamed = directory.with_name("0002-least-recently-used-cache")
    directory.rename(renamed)
    (renamed / "meta.yaml").write_text(
        (renamed / "meta.yaml")
        .read_text()
        .replace("slug: lru-cache", "slug: least-recently-used-cache")
    )
    row = invoke().output.splitlines()[2]
    assert row.startswith("0002  least-recent...   medium  segment-tre...   ")


def test_filters(environment):
    assert invoke("--difficulty", "medium").output.splitlines()[1:] == [
        "0002  lru-cache         medium  linked-list      new       -           py"
    ]


def test_no_match_says_so(environment):
    assert invoke("--lang", "kotlin").output == "no problems match\n"


def test_invalid_meta_is_a_content_error(environment):
    (environment.root / "problems/0001-two-sum/meta.yaml").write_text("id: 1\n")
    assert invoke().exit_code == ExitCode.CONTENT_ERROR
