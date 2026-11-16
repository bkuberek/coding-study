from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.config import Config, ProfileSettings
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import ReviewState, ScheduleEntry
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import list_problems
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import NOW, make_environment, repository_root

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
HEADER = "SLUG              DIFF    PATTERN          STATUS        DUE         REFS"


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
        "two-sum           easy    arrays-hashing   new           -           py",
        "lru-cache         medium  linked-list      new           -           py",
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
    assert row == "two-sum           easy    arrays-hashing   passed        2026-10-27  py"


def test_a_problem_with_an_attempt_in_progress_reads_in_progress_in_words(environment):
    environment.progress.add_attempt(NewAttempt("two-sum", Language.PYTHON, AttemptMode.NEW, NOW))
    row = invoke().output.splitlines()[1]
    assert row == "two-sum           easy    arrays-hashing   in progress   -           py"


@pytest.mark.parametrize("spelling", ["in_progress", "in-progress"])
def test_the_status_filter_takes_in_progress_spelled_either_way(environment, spelling):
    environment.progress.add_attempt(NewAttempt("two-sum", Language.PYTHON, AttemptMode.NEW, NOW))
    rows = invoke("--status", spelling).output.splitlines()[1:]
    assert [row.split()[0] for row in rows] == ["two-sum"]


def test_the_status_filter_does_not_take_the_spaced_words(environment):
    assert invoke("--status", "in progress").exit_code == ExitCode.USAGE_ERROR


def test_an_unknown_status_is_a_usage_error_that_lists_the_statuses(environment):
    result = invoke("--status", "finished")
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert "in_progress" in result.output


def test_the_status_filter_new_leaves_a_problem_in_progress_out(environment):
    environment.progress.add_attempt(NewAttempt("two-sum", Language.PYTHON, AttemptMode.NEW, NOW))
    rows = invoke("--status", "new").output.splitlines()[1:]
    assert [row.split()[0] for row in rows] == ["lru-cache"]


def test_attempted_is_written_in_full(environment):
    attempt = environment.progress.add_attempt(
        NewAttempt("two-sum", Language.PYTHON, AttemptMode.NEW, NOW)
    )
    environment.progress.update_attempt(replace(attempt, status=AttemptStatus.FAILED))
    row = invoke().output.splitlines()[1]
    assert row == "two-sum           easy    arrays-hashing   attempted     -           py"


def test_long_slugs_and_patterns_are_truncated(environment):
    meta = environment.root / "problems/lru-cache/meta.yaml"
    meta.write_text(meta.read_text().replace("[linked-list]", "[segment-tree-fenwick]"))
    directory = environment.root / "problems/lru-cache"
    renamed = directory.with_name("least-recently-used-cache")
    directory.rename(renamed)
    (renamed / "meta.yaml").write_text(
        (renamed / "meta.yaml")
        .read_text()
        .replace("slug: lru-cache", "slug: least-recently-used-cache")
    )
    row = invoke().output.splitlines()[2]
    assert row.startswith("least-recent...   medium  segment-tre...   ")


def test_filters(environment):
    assert invoke("--difficulty", "medium").output.splitlines()[1:] == [
        "lru-cache         medium  linked-list      new           -           py"
    ]


def test_no_match_says_so(environment):
    assert invoke("--lang", "kotlin").output == "no problems match\n"


def test_invalid_meta_is_a_content_error(environment):
    (environment.root / "problems/two-sum/meta.yaml").write_text("id: 1\n")
    assert invoke().exit_code == ExitCode.CONTENT_ERROR


BACKEND_LINE = (
    "filtered by your profile: 1 of 2 problems · domains backend · --widen all shows all 2"
)


def use_profile(monkeypatch, environment, **changes) -> None:
    profiled = replace(environment, **changes)
    monkeypatch.setattr(list_problems, "load_catalog_environment", lambda *_: profiled)


@pytest.fixture
def backend_profile(environment, monkeypatch):
    config = Config(profile=ProfileSettings(domains=("backend",)))
    use_profile(monkeypatch, environment, config=config)


def test_the_profile_line_is_plain_text_when_stdout_is_not_a_terminal(backend_profile):
    result = invoke()
    assert result.output.splitlines()[1:] == [
        "lru-cache         medium  linked-list      new           -           py",
        BACKEND_LINE,
    ]
    assert "\x1b" not in result.output


def test_the_profile_line_is_dim_on_a_terminal(backend_profile):
    result = runner.invoke(cli.app, ["list"], env={"FORCE_COLOR": "1"})
    assert result.output.splitlines()[-1] == f"\x1b[2m{BACKEND_LINE}\x1b[0m"


def test_the_profile_line_goes_to_standard_output(backend_profile):
    result = invoke()
    assert BACKEND_LINE in result.stdout
    assert "filtered by" not in result.stderr


def test_no_profile_line_with_widen_all(backend_profile):
    assert invoke("--widen", "all").output.splitlines()[1:] == [
        "two-sum           easy    arrays-hashing   new           -           py",
        "lru-cache         medium  linked-list      new           -           py",
    ]


def test_no_profile_line_when_the_narrowed_profile_hides_nothing(environment, monkeypatch):
    config = Config(profile=ProfileSettings(domains=("algorithms",)))
    use_profile(monkeypatch, environment, config=config)
    assert "filtered by" not in invoke().output


def test_the_workspace_languages_narrow_the_listing_and_the_line(environment, monkeypatch):
    use_profile(monkeypatch, environment, workspace_languages=(Language.GO,))
    assert invoke().output.splitlines() == [
        "no problems match",
        "filtered by your profile: 0 of 2 problems · languages go · --widen all shows all 2",
    ]
    assert invoke("--widen", "lang").output == invoke("--widen", "all").output


def test_an_unknown_widening_is_a_usage_error(environment):
    result = invoke("--widen", "languages")
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert 'unknown widening "languages"; use lang, role, domain or all' in result.stderr
