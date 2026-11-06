import json
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
from tests.fakes import NOW, RecordingEditor, jdk_of, repository_root
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


@pytest.fixture
def with_a_practical_problem(tmp_path, editor, monkeypatch, tmp_path_factory):
    """The first catalog problems and the banking system, a `practical` problem."""
    problems = copy_catalog_problems(
        tmp_path_factory.mktemp("catalog"), (*FIRST_CATALOG, "0187-banking-system")
    )
    environment = e2e_environment(repository_root(tmp_path, problems), editor=editor)
    monkeypatch.setattr(next_problem, "load_environment", lambda *_: environment)
    return environment


def test_a_domain_searches_every_track(with_a_practical_problem):
    assert invoke("--domain", "fintech").output.splitlines() == [
        "new     banking-system  (hard · practical)  weakest track: practical (0.75)",
        "start   cstudy start banking-system --lang python",
    ]


def test_a_role_searches_every_track(with_a_practical_problem):
    assert invoke("--role", "backend").output.splitlines()[0].startswith("new     banking-system")


def test_a_scope_searches_every_track(with_a_practical_problem):
    assert invoke("--scope", "function").output.splitlines()[0].startswith("new     two-sum")


def test_a_track_given_narrows_a_label_filter(with_a_practical_problem):
    result = invoke("--domain", "fintech", "--track", "dsa")
    assert result.output == "nothing due and no new problems in scope\n"


def test_a_domain_no_problem_names_finds_nothing(with_a_practical_problem):
    assert invoke("--domain", "security").output == "nothing due and no new problems in scope\n"


@pytest.mark.parametrize("flag", ["--domain", "--role", "--scope"])
def test_a_label_outside_its_list_is_a_usage_error(environment, flag):
    assert invoke(flag, "no-such-value").exit_code == ExitCode.USAGE_ERROR


def test_command_is_registered():
    assert "next" in {command.name for command in cli.app.registered_commands}


def document(*arguments: str):
    return json.loads(invoke("--json", *arguments).stdout)


def test_json_describes_a_new_pick(environment):
    assert document() == {
        "pick": "new",
        "slug": "two-sum",
        "title": "Two Sum",
        "kind": "function",
        "difficulty": "easy",
        "group": "arrays-hashing",
        "reason": "weakest pattern: arrays-hashing (0.75)",
        "language": "python",
        "start": "cstudy start two-sum --lang python",
    }


def test_json_describes_a_review(environment):
    schedule_review(environment, "lru-cache", overdue_days=3)
    found = document()
    assert (found["pick"], found["reason"]) == ("review", "overdue 3d, interval 7d")


def test_json_starts_in_the_language_given(environment):
    found = document("--lang", "kotlin")
    assert (found["language"], found["start"]) == (
        "kotlin",
        "cstudy start two-sum --lang kotlin",
    )


def test_json_with_nothing_to_pick_says_so(environment):
    assert document("--track", "practical") == {
        "pick": None,
        "message": "nothing due and no new problems in scope",
    }


def test_json_and_start_together_are_a_usage_error(environment):
    result = invoke("--json", "--start")
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: --json excludes --start\n",
    )


def test_json_and_start_together_start_nothing(environment):
    invoke("--json", "--start")
    assert environment.progress.active_attempt() is None


JDK_27_REASON = "JDK 27 (JAVA_HOME) cannot run java problems; cstudy supports JDK 21 to 26"


def on_jdk(environment, monkeypatch, jdk) -> None:
    selecting = replace(environment, jdk=jdk)
    monkeypatch.setattr(next_problem, "load_environment", lambda *_: selecting)


def test_a_jdk_that_cannot_run_java_leaves_nothing_to_pick_in_java(environment, monkeypatch):
    on_jdk(environment, monkeypatch, jdk_of(27))
    result = invoke("--lang", "java")
    assert (result.exit_code, result.output) == (
        ExitCode.SUCCESS,
        f"nothing to pick: {JDK_27_REASON}\n",
    )


def test_the_json_message_says_so_too(environment, monkeypatch):
    on_jdk(environment, monkeypatch, jdk_of(27))
    assert document("--lang", "java") == {
        "pick": None,
        "message": f"nothing to pick: {JDK_27_REASON}",
    }


def test_the_same_jdk_leaves_python_alone(environment, monkeypatch):
    on_jdk(environment, monkeypatch, jdk_of(27))
    assert invoke().output.splitlines()[0].startswith("new")


def test_start_never_starts_a_problem_the_jdk_cannot_run(environment, monkeypatch):
    on_jdk(environment, monkeypatch, jdk_of(27))
    result = invoke("--lang", "java", "--start")
    assert result.exit_code == ExitCode.SUCCESS
    assert environment.progress.active_attempt() is None
