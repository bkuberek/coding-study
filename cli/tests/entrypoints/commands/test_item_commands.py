from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.fs_study_guides import FsStudyGuides
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import done, solution, start, test
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import FakeClock, RecordingEditor, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
NOTES = "notes/system-design/url-shortener.md"
STATEMENT = ".statements/url-shortener.md"


@pytest.fixture
def editor() -> RecordingEditor:
    return RecordingEditor()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def environment(tmp_path, editor, clock, monkeypatch):
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    environment = make_environment(root, editor=editor, clock=clock)
    for command in (start, solution, done, test):
        monkeypatch.setattr(command, "load_environment", lambda *_: environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["--no-color", *arguments])


def test_start_prints_the_item_and_its_files(environment):
    assert invoke("start", "url-shortener").output.splitlines() == [
        "url-shortener · medium · system-design · 45 min",
        f"notes      {NOTES}",
        f"prompt     {STATEMENT}",
        "next       answer in the notes, then cstudy solution url-shortener",
    ]


def test_start_prints_each_located_study_guide(tmp_path, monkeypatch, environment):
    guides = tmp_path / "study-guides"
    guides.mkdir()
    (guides / "distributed-systems-study-guide.md").write_text("# Guide\n")
    guided = replace(environment, study_guides=FsStudyGuides(guides))
    monkeypatch.setattr(start, "load_environment", lambda *_: guided)
    location = (guides / "distributed-systems-study-guide.md").as_uri()
    assert invoke("start", "url-shortener").output.splitlines()[3] == (
        f"guide      {location}#databases"
    )


def test_start_opens_the_notes_and_the_prompt(environment, editor):
    invoke("start", "url-shortener")
    assert editor.opened == [[environment.root / NOTES, environment.root / STATEMENT]]


def test_start_rejects_a_language(environment):
    result = invoke("start", "url-shortener", "--lang", "kotlin")
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: url-shortener is not autograded; --lang applies to problems\n",
    )


def test_resuming_says_so(environment):
    invoke("start", "url-shortener")
    assert "attempt    resumed" in invoke("start", "url-shortener").output.splitlines()


def test_solution_shows_the_rubric_then_the_reference(environment):
    output = invoke("solution", "url-shortener").output
    assert output.index("Handles expiry") < output.index("Pre-generated random keys")


def test_solution_title(environment):
    first = invoke("solution", "url-shortener").output.splitlines()[0]
    assert first == "URL Shortener · system-design"


def test_solution_never_asks_before_revealing(environment):
    invoke("start", "url-shortener")
    assert "Reveal the solution?" not in invoke("solution", "url-shortener").output


@pytest.mark.parametrize("flag", [["--lang", "java"], ["--approach", "x"], ["--all"]])
def test_solution_rejects_problem_options(environment, flag):
    assert invoke("solution", "url-shortener", *flag).exit_code == ExitCode.USAGE_ERROR


def test_done_takes_a_rating(environment, clock):
    invoke("start", "url-shortener")
    clock.advance(timedelta(minutes=40))
    assert invoke("done", "--rating", "ok").output.splitlines() == [
        "url-shortener · passed · 40m 00s · rating ok · hints 0",
        "next review  2026-10-27 (in 3 days) · ease 2.50",
    ]


def test_done_rejects_giving_up(environment):
    invoke("start", "url-shortener")
    result = invoke("done", "--gave-up")
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: url-shortener is self-graded; finish with --rating easy|ok|hard\n",
    )


def test_test_is_not_available_for_items(environment):
    invoke("start", "url-shortener")
    result = invoke("test")
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: url-shortener is not autograded\n",
    )
