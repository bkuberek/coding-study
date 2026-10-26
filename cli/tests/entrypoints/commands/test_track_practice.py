"""`cstudy list` and `cstudy next` over non-autograded items, and the Phase 6 practice loop."""

from datetime import timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.domain.config import Config, NextSettings
from coding_study.domain.problem import Track
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import done, list_problems, next_problem, solution, start
from tests.fakes import FakeClock, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
COMMANDS = (done, list_problems, next_problem, solution, start)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def environment(tmp_path, clock, monkeypatch):
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    environment = make_environment(root, clock=clock, config=Config(open_on_start=False))
    for command in COMMANDS:
        loader = "load_catalog_environment" if command is list_problems else "load_environment"
        monkeypatch.setattr(command, loader, lambda *_: environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["--no-color", *arguments])


def test_list_track_shows_its_items(environment):
    assert invoke("list", "--track", "system-design").output.splitlines() == [
        "ID    SLUG              DIFF    PATTERN          STATUS    DUE         REFS",
        "-     url-shortener     medium  system-design    new       -           -",
        "-     news-feed         hard    system-design    new       -           -",
    ]


def test_list_shows_items_after_problems(environment):
    slugs = [line.split()[1] for line in invoke("list").output.splitlines()[1:]]
    assert slugs == ["two-sum", "lru-cache", "url-shortener", "news-feed", "retry-wrapper"]


def test_list_content_filter_applies_to_items(environment):
    output = invoke("list", "--track", "system-design", "--content", "draft").output
    assert [line.split()[1] for line in output.splitlines()[1:]] == ["news-feed"]


def test_list_pattern_filter_leaves_items_out(environment):
    assert "url-shortener" not in invoke("list", "--pattern", "arrays-hashing").output


def test_next_track_picks_a_new_item(environment):
    assert invoke("next", "--track", "system-design").output.splitlines() == [
        "new     url-shortener  (medium · system-design)  weakest track: system-design (0.75)",
        "start   cstudy start url-shortener",
    ]


def test_next_start_line_for_an_item_ignores_lang(environment):
    output = invoke("next", "--track", "system-design", "--lang", "kotlin").output
    assert output.splitlines()[1] == "start   cstudy start url-shortener"


def test_next_defaults_to_the_config_tracks(environment):
    assert (
        invoke("next").output.splitlines()[0].startswith("new     two-sum  (easy · arrays-hashing)")
    )


def test_next_with_nothing_in_scope(environment):
    result = invoke("next", "--track", "behavioral")
    assert (result.exit_code, result.output) == (0, "nothing due and no new problems in scope\n")


def test_next_review_names_the_overdue_days(environment, clock):
    invoke("start", "url-shortener")
    invoke("done", "--rating", "ok")
    clock.advance(timedelta(days=5))
    assert invoke("next", "--track", "system-design").output.splitlines()[0] == (
        "review  url-shortener  (medium · system-design)  overdue 2d, interval 3d"
    )


def test_next_start_starts_the_pick(environment):
    invoke("next", "--track", "code-review", "--start")
    attempt = environment.progress.active_attempt()
    assert (attempt.slug, attempt.language) == ("retry-wrapper", None)


def test_next_start_prints_the_start_report(environment):
    output = invoke("next", "--track", "code-review", "--start").output.splitlines()
    assert output[1] == "retry-wrapper · easy · code-review · 20 min"


def test_next_lang_is_offered_for_problems(environment):
    assert invoke("next", "--lang", "python").output.splitlines()[1] == (
        "start   cstudy start two-sum --lang python"
    )


def test_next_new_and_review_together_are_a_usage_error(environment):
    assert invoke("next", "--new", "--review").exit_code == 3


def test_config_tracks_reach_items(environment, monkeypatch):
    tracks = Config(open_on_start=False, next=NextSettings((Track.CODE_REVIEW,)))
    configured = make_environment(environment.root, config=tracks)
    monkeypatch.setattr(next_problem, "load_environment", lambda *_: configured)
    assert invoke("next").output.startswith("new     retry-wrapper")


def test_practice_loop_on_a_system_design_item(environment, clock):
    """Phase 6 exit criterion: cstudy next --track system-design, then start, solution and done."""
    picked = invoke("next", "--track", "system-design").output.splitlines()[0].split()[1]
    invoke("start", picked)
    environment.workspace.write_text(
        "notes/system-design/url-shortener.md", "# URL Shortener: Notes\n"
    )
    clock.advance(timedelta(minutes=45))
    revealed = invoke("solution", picked).output
    finished = invoke("done", "--rating", "hard").output.splitlines()
    after = invoke("next", "--track", "system-design").output
    assert (picked, "Pre-generated random keys" in revealed, finished[1][:24], after) == (
        "url-shortener",
        True,
        "next review  2026-10-26 ",
        "nothing due and no new problems in scope\n",
    )
