from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import solution
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment
from tests.fakes import repository_root as copy_repository

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
REVEAL_PROMPT = "Reveal the solution? The attempt will be graded as again. [y/N]"


@pytest.fixture
def environment(tmp_path, monkeypatch):
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(copy_repository(tmp_path, PRACTICE), toolchains=toolchains)
    monkeypatch.setattr(solution, "load_environment", lambda *_: environment)
    return environment


def invoke(*arguments: str, answer: str = ""):
    return runner.invoke(cli.app, ["--no-color", "solution", *arguments], input=answer)


def test_shows_the_overview(environment):
    assert "n is tiny" in invoke("two-sum").output


def test_shows_the_default_approach_explanation(environment):
    assert "Remember each value's position" in invoke("two-sum").output


def test_shows_the_default_approach_code(environment):
    assert "seen: dict[int, int] = {}" in invoke("two-sum").output


def test_hides_other_approaches(environment):
    assert "Try every pair of positions" not in invoke("two-sum").output


def test_all_approaches(environment):
    assert "Try every pair of positions" in invoke("two-sum", "--all").output


def test_explanation_only(environment):
    assert "seen: dict[int, int]" not in invoke("two-sum", "--explanation-only").output


def test_missing_language_lists_the_available_ones(environment):
    assert "no java reference; available: python" in invoke("two-sum", "--lang", "java").output


def test_unknown_approach_is_a_usage_error(environment):
    assert invoke("two-sum", "--approach", "greedy").exit_code == ExitCode.USAGE_ERROR


def test_unsolved_attempt_asks_before_revealing(environment):
    start_attempt(environment, StartRequest("two-sum"))
    assert REVEAL_PROMPT in invoke("two-sum", answer="y\n").output


def test_declining_shows_nothing(environment):
    start_attempt(environment, StartRequest("two-sum"))
    result = invoke("two-sum", answer="n\n")
    assert ("seen: dict" in result.output, result.exit_code) == (False, 0)


def test_declining_keeps_the_attempt_unmarked(environment):
    start_attempt(environment, StartRequest("two-sum"))
    invoke("two-sum", answer="n\n")
    attempt = environment.progress.active_attempt()
    assert attempt is not None
    assert not attempt.solution_revealed


def test_confirming_marks_the_attempt(environment):
    start_attempt(environment, StartRequest("two-sum"))
    invoke("two-sum", answer="y\n")
    attempt = environment.progress.active_attempt()
    assert attempt is not None
    assert attempt.solution_revealed


def test_yes_skips_the_question(environment):
    start_attempt(environment, StartRequest("two-sum"))
    result = invoke("two-sum", "--yes")
    assert (REVEAL_PROMPT in result.output, "seen: dict" in result.output) == (False, True)
