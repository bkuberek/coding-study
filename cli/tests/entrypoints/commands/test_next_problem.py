from dataclasses import replace
from datetime import timedelta

import pytest
from typer.testing import CliRunner

from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.config import Config
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import ReviewState, ScheduleEntry
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import next_problem
from coding_study.entrypoints.shared import ExitCode
from tests.e2e import e2e_environment
from tests.fakes import NOW, RecordingEditor, repository_root
from tests.helpers import FIRST_CATALOG, copy_catalog_problems

runner = CliRunner()


@pytest.fixture
def editor() -> RecordingEditor:
    return RecordingEditor()


@pytest.fixture
def problems(tmp_path_factory):
    return copy_catalog_problems(tmp_path_factory.mktemp("catalog"), FIRST_CATALOG)


@pytest.fixture
def environment(tmp_path, editor, monkeypatch, problems):
    environment = e2e_environment(repository_root(tmp_path, problems), editor=editor)
    monkeypatch.setattr(next_problem, "load_environment", lambda *_: environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["next", *arguments])


def schedule_review(environment, slug: str, overdue_days: int, interval: int = 7) -> None:
    progress = environment.progress
    attempt = progress.add_attempt(NewAttempt(slug, Language.PYTHON, AttemptMode.NEW, NOW))
    progress.update_attempt(
        replace(attempt, status=AttemptStatus.PASSED, ended_at=NOW, grade=Grade.OK)
    )
    due_on = NOW.date() - timedelta(days=overdue_days)
    state = ReviewState(interval_days=interval, reps=2)
    progress.save_schedule_entry(ScheduleEntry(slug, state, due_on, Grade.OK, NOW))


def test_a_new_problem_names_the_weakest_pattern(environment):
    assert invoke().output.splitlines() == [
        "new     two-sum  (easy · arrays-hashing)  weakest pattern: arrays-hashing (0.75)",
        "start   cstudy start two-sum --lang python",
    ]


def test_a_review_names_the_overdue_days_and_interval(environment):
    schedule_review(environment, "lru-cache", overdue_days=3)
    assert invoke().output.splitlines()[0] == (
        "review  lru-cache  (medium · linked-list)  overdue 3d, interval 7d"
    )


def test_a_review_due_today(environment):
    schedule_review(environment, "lru-cache", overdue_days=0, interval=3)
    assert invoke().output.splitlines()[0].endswith("due today, interval 3d")


def test_the_start_hint_uses_the_language_given(environment):
    assert invoke("--lang", "kotlin").output.splitlines()[1] == (
        "start   cstudy start two-sum --lang kotlin"
    )


def test_nothing_in_scope(environment):
    result = invoke("--track", "practical")
    assert (result.exit_code, result.output) == (0, "nothing due and no new problems in scope\n")


def test_new_and_review_together_are_a_usage_error(environment):
    assert invoke("--new", "--review").exit_code == ExitCode.USAGE_ERROR


def test_review_only_without_reviews_finds_nothing(environment):
    assert invoke("--review").output == "nothing due and no new problems in scope\n"


def test_start_begins_the_attempt(environment):
    invoke("--start")
    attempt = environment.progress.active_attempt()
    assert (attempt.slug, attempt.language) == ("two-sum", Language.PYTHON)


def test_start_prints_the_pick_and_the_started_files(environment):
    assert invoke("--start").output.splitlines() == [
        "new     two-sum  (easy · arrays-hashing)  weakest pattern: arrays-hashing (0.75)",
        "two-sum · easy · arrays-hashing · python",
        "stub       python/practice/two_sum.py",
        "statement  .statements/two-sum.md",
        "next       cstudy test --watch",
    ]


def test_start_opens_the_editor(environment, editor):
    invoke("--start")
    assert len(editor.opened) == 1


def test_start_respects_open_on_start(environment, editor, monkeypatch):
    closed = replace(environment, config=Config(open_on_start=False))
    monkeypatch.setattr(next_problem, "load_environment", lambda *_: closed)
    invoke("--start")
    assert editor.opened == []


def test_start_with_nothing_to_pick_starts_nothing(environment):
    invoke("--start", "--track", "practical")
    assert environment.progress.active_attempt() is None


def test_an_unknown_pattern_is_a_usage_error(environment):
    assert invoke("--pattern", "no-such-pattern").exit_code == ExitCode.USAGE_ERROR


def test_command_is_registered():
    assert "next" in {command.name for command in cli.app.registered_commands}
