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
from coding_study.domain.config import Config, ProfileSettings
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
from tests.helpers import FIRST_CATALOG, FIXTURE_RUBRIC_PROBLEMS, copy_catalog_problems

runner = CliRunner()
SLICE = (*FIRST_CATALOG, "group-anagrams", "first-missing-positive")
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
        repository_root(tmp_path, problems, FIXTURE_RUBRIC_PROBLEMS),
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


def test_a_lang_outside_the_workspaces_languages_exits_3_with_the_lang_add_hint(
    environment, monkeypatch
):
    narrowed = replace(environment, workspace_languages=(Language.PYTHON,))
    monkeypatch.setattr(mock, "load_environment", lambda *_: narrowed)
    result = invoke("mock", "--lang", "kotlin")
    assert (result.exit_code, started(environment)) == (ExitCode.USAGE_ERROR, [])
    assert "kotlin is not one of this workspace's languages (python): cstudy lang add kotlin" in (
        result.output
    )


def test_the_mock_starts_in_the_first_workspace_language_when_the_default_is_not_one(
    environment, monkeypatch
):
    narrowed = replace(environment, workspace_languages=(Language.KOTLIN, Language.GO))
    monkeypatch.setattr(mock, "load_environment", lambda *_: narrowed)
    output = invoke("mock").output
    assert output.splitlines()[0] == "mock interview · 2 problems · 45 min shared timer · kotlin"


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


# The learner profile (docs/specs/cli.md#cstudy-mock)

BACKEND_LINE = (
    "filtered by your profile: picked from 1 of 3 new medium and hard problems · "
    "domains backend · --widen all picks from all 3"
)


def edit_meta(environment, slug: str, old: str, new: str) -> None:
    meta = environment.root / "problems" / slug / "meta.yaml"
    meta.write_text(meta.read_text().replace(old, new, 1))


def use_profile(monkeypatch, environment, **changes) -> None:
    profiled = replace(environment, **changes)
    monkeypatch.setattr(mock, "load_environment", lambda *_: profiled)


@pytest.fixture
def backend_profile(environment, monkeypatch):
    edit_meta(environment, "lru-cache", "domains: [algorithms]", "domains: [backend]")
    use_profile(
        monkeypatch, environment, config=Config(profile=ProfileSettings(domains=("backend",)))
    )


def test_the_profile_narrows_the_picks_and_the_report_ends_with_its_line(
    environment, backend_profile
):
    result = invoke("mock")
    assert started(environment) == ["lru-cache"]
    assert (
        result.output.splitlines()[0]
        == "mock interview · 1 of 2 problems · 45 min shared timer · python"
    )
    assert result.output.splitlines()[-1] == BACKEND_LINE


def test_the_profile_line_is_dim_on_a_terminal_and_goes_to_standard_output(backend_profile):
    result = runner.invoke(cli.app, ["mock"], env={"FORCE_COLOR": "1"})
    assert result.stdout.splitlines()[-1] == f"\x1b[2m{BACKEND_LINE}\x1b[0m"
    assert "filtered by" not in result.stderr


def test_widen_all_picks_from_every_problem_and_prints_no_line(environment, backend_profile):
    result = invoke("mock", "--widen", "all")
    assert started(environment) == ["group-anagrams", "lru-cache"]
    assert "filtered by" not in result.output


def test_widen_role_keeps_the_domains_of_the_profile(environment, backend_profile):
    assert BACKEND_LINE in invoke("mock", "--widen", "role").output
    assert started(environment) == ["lru-cache"]


@pytest.mark.parametrize("value", ["lang", "everything"])
def test_widen_takes_only_role_domain_and_all(environment, value):
    result = invoke("mock", "--widen", value)
    assert (result.exit_code, started(environment)) == (ExitCode.USAGE_ERROR, [])
    assert f'unknown widening "{value}"; use role, domain or all' in result.stderr


def test_a_profile_that_left_nothing_says_so_and_prints_no_line(environment, monkeypatch):
    config = Config(profile=ProfileSettings(domains=("security",)))
    use_profile(monkeypatch, environment, config=config)
    result = invoke("mock")
    assert (result.exit_code, started(environment)) == (0, [])
    assert result.output == (
        "no new medium or hard problems in your profile (domains security); "
        "widen with cstudy mock --widen all\n"
    )


def test_domain_picks_the_problems_that_list_it_without_widening_the_tracks(environment):
    edit_meta(environment, "lru-cache", "domains: [algorithms]", "domains: [backend]")
    invoke("mock", "--domain", "backend")
    assert started(environment) == ["lru-cache"]


def test_role_picks_the_problems_that_list_it_and_not_general_ones(environment):
    edit_meta(environment, "lru-cache", "job_roles: [general]", "job_roles: [platform]")
    invoke("mock", "--role", "platform")
    assert started(environment) == ["lru-cache"]


def test_a_domain_given_replaces_the_profiles_domains(environment, monkeypatch):
    config = Config(profile=ProfileSettings(domains=("security",)))
    use_profile(monkeypatch, environment, config=config)
    result = invoke("mock", "--domain", "algorithms")
    assert started(environment) == ["group-anagrams", "lru-cache"]
    assert "filtered by" not in result.output


@pytest.mark.parametrize("flag", ["--domain", "--role"])
def test_a_label_outside_its_list_is_a_usage_error(environment, flag):
    result = invoke("mock", flag, "no-such-label")
    assert (result.exit_code, started(environment)) == (ExitCode.USAGE_ERROR, [])


def test_a_problem_that_lacks_the_default_language_starts_in_one_it_lists(environment, monkeypatch):
    edit_meta(
        environment, "group-anagrams", "estimate_minutes:", "languages: [go]\nestimate_minutes:"
    )
    use_profile(monkeypatch, environment, workspace_languages=(Language.PYTHON, Language.GO))
    lines = invoke("mock").output.splitlines()
    assert lines[0] == "mock interview · 2 problems · 45 min shared timer · go, python"
    languages = {a.slug: a.language for a in environment.progress.attempts_in_progress()}
    assert languages == {"group-anagrams": Language.GO, "lru-cache": Language.PYTHON}


def test_lang_picks_only_the_problems_that_list_it(environment):
    edit_meta(
        environment, "group-anagrams", "estimate_minutes:", "languages: [go]\nestimate_minutes:"
    )
    lines = invoke("mock", "--lang", "python").output.splitlines()
    assert started(environment) == ["first-missing-positive", "lru-cache"]
    assert lines[0] == "mock interview · 2 problems · 45 min shared timer · python"


def test_a_problem_no_workspace_language_can_start_is_not_picked(environment, monkeypatch):
    edit_meta(
        environment, "group-anagrams", "estimate_minutes:", "languages: [go]\nestimate_minutes:"
    )
    use_profile(monkeypatch, environment, workspace_languages=(Language.PYTHON,))
    invoke("mock")
    assert started(environment) == ["first-missing-positive", "lru-cache"]
