"""`cstudy mock` over a fixed catalog slice: two-sum and invert-binary-tree (easy), lru-cache
(medium linked-list), group-anagrams (medium arrays-hashing) and first-missing-positive (hard
arrays-hashing), plus the fixture items."""

from dataclasses import replace
from datetime import timedelta

import pytest
from typer.testing import CliRunner

from coding_study.application.complete_attempt import DoneRequest, complete_attempt
from coding_study.application.ports import StubGenerator
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import AttemptMode
from coding_study.domain.config import Config
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import hint, mock, solution
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import (
    FakeStubGenerator,
    FakeToolchains,
    RecordingEditor,
    make_environment,
    repository_root,
)
from tests.helpers import FIRST_CATALOG, FIXTURE_TRACKS, copy_catalog_problems

runner = CliRunner()
SLICE = (*FIRST_CATALOG, "0007-group-anagrams", "0014-first-missing-positive")
FORTY_FIVE_MINUTES = 45 * 60


@pytest.fixture
def problems(tmp_path_factory):
    return copy_catalog_problems(tmp_path_factory.mktemp("catalog"), SLICE)


@pytest.fixture
def editor() -> RecordingEditor:
    return RecordingEditor()


@pytest.fixture
def environment(tmp_path, monkeypatch, problems, editor):
    generators: dict[Language, StubGenerator] = {
        language: FakeStubGenerator() for language in Language
    }
    environment = make_environment(
        repository_root(tmp_path, problems, FIXTURE_TRACKS),
        toolchains=FakeToolchains(stub_generators=generators),
        editor=editor,
    )
    for module in (mock, hint, solution):
        monkeypatch.setattr(module, "load_environment", lambda *_: environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, list(arguments))


def started(environment) -> list[str]:
    return [attempt.slug for attempt in environment.progress.attempts_in_progress()]


def test_mock_starts_two_new_problems_from_different_groups(environment):
    invoke("mock")
    assert started(environment) == ["group-anagrams", "lru-cache"]


def test_mock_attempts_have_mode_mock(environment):
    invoke("mock")
    modes = {attempt.mode for attempt in environment.progress.attempts_in_progress()}
    assert modes == {AttemptMode.MOCK}


def test_mock_attempts_share_one_timer(environment):
    invoke("mock")
    attempts = environment.progress.attempts_in_progress()
    timers = {(attempt.started_at, attempt.time_limit_s) for attempt in attempts}
    assert timers == {(environment.clock.now(), FORTY_FIVE_MINUTES)}


def test_mock_report(environment):
    assert invoke("mock").output.splitlines() == [
        "mock interview · 2 problems · 45 min shared timer · python",
        "1  group-anagrams  (medium · arrays-hashing)  weakest pattern: arrays-hashing (0.75)",
        "   stub       python/practice/group_anagrams.py",
        "   statement  .statements/group-anagrams.md",
        "2  lru-cache  (medium · linked-list)  weakest pattern: linked-list (0.75)",
        "   stub       python/practice/lru_cache.py",
        "   statement  .statements/lru-cache.md",
        "locked     cstudy hint and cstudy solution, until the timer ends or every problem is done",
        "next       cstudy test group-anagrams --watch",
    ]


def test_minutes_set_the_timer(environment):
    invoke("mock", "--minutes", "30")
    assert {a.time_limit_s for a in environment.progress.attempts_in_progress()} == {1800}


def test_count_sets_the_number_of_problems(environment):
    invoke("mock", "--count", "3")
    assert started(environment) == ["group-anagrams", "lru-cache", "first-missing-positive"]


def test_a_count_beyond_the_scope_starts_what_there_is(environment):
    lines = invoke("mock", "--count", "4").output.splitlines()
    assert lines[0] == "mock interview · 3 of 4 problems · 45 min shared timer · python"


def test_lang_writes_stubs_in_that_language(environment):
    output = invoke("mock", "--lang", "kotlin").output
    assert "   stub       jvm/kotlin/src/main/kotlin/practice/lru_cache/" in output


def test_track_reaches_items(environment):
    invoke("mock", "--track", "system-design", "--count", "1")
    assert started(environment) == ["url-shortener"]


def test_an_item_reports_its_notes(environment):
    lines = invoke("mock", "--track", "system-design", "--count", "1").output.splitlines()
    assert lines[:4] == [
        "mock interview · 1 problem · 45 min shared timer",
        "1  url-shortener  (medium · system-design)  weakest track: system-design (0.75)",
        "   notes      notes/system-design/url-shortener.md",
        "   prompt     .statements/url-shortener.md",
    ]


def test_nothing_in_scope_starts_nothing(environment):
    result = invoke("mock", "--track", "practical")
    assert (result.exit_code, result.output, started(environment)) == (
        0,
        "no new medium or hard problems in scope\n",
        [],
    )


def test_mock_opens_every_file_in_one_editor_call(environment, editor):
    invoke("mock")
    assert len(editor.opened) == 1


def test_mock_opens_four_files_for_two_problems(environment, editor):
    invoke("mock")
    assert len(editor.opened[0]) == 4


def test_mock_respects_open_on_start(environment, editor, monkeypatch):
    closed = replace(environment, config=Config(open_on_start=False))
    monkeypatch.setattr(mock, "load_environment", lambda *_: closed)
    invoke("mock")
    assert editor.opened == []


def test_a_second_mock_while_one_runs_is_a_usage_error(environment):
    invoke("mock")
    assert invoke("mock").exit_code == ExitCode.USAGE_ERROR


def test_hints_are_locked_during_the_mock(environment):
    invoke("mock")
    result = invoke("hint", "lru-cache")
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: cstudy hint is locked during the mock interview (group-anagrams, lru-cache; "
        "45:00 left); it unlocks when the timer ends or every problem is done\n",
    )


def test_solutions_are_locked_during_the_mock(environment):
    invoke("mock")
    assert invoke("solution", "two-sum", "--yes").exit_code == ExitCode.USAGE_ERROR


def test_item_solutions_are_locked_during_the_mock(environment):
    invoke("mock")
    assert invoke("solution", "url-shortener").exit_code == ExitCode.USAGE_ERROR


def test_hints_unlock_when_the_timer_ends(environment):
    invoke("mock")
    environment.clock.advance(timedelta(minutes=45))
    assert invoke("hint", "lru-cache").exit_code == ExitCode.SUCCESS


def test_hints_unlock_when_every_problem_is_done(environment):
    invoke("mock")
    for slug in ("group-anagrams", "lru-cache"):
        complete_attempt(environment, DoneRequest(slug, gave_up=True))
    start_attempt(environment, StartRequest("two-sum"))
    assert invoke("hint", "two-sum").exit_code == ExitCode.SUCCESS


def test_a_finished_problem_keeps_the_lock_while_another_runs(environment):
    invoke("mock")
    complete_attempt(environment, DoneRequest("group-anagrams", gave_up=True))
    assert "lru-cache; 45:00 left" in invoke("hint", "lru-cache").stderr


def test_command_is_registered():
    assert "mock" in {command.name for command in cli.app.registered_commands}
