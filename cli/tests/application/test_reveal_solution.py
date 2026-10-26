from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.reveal_solution import (
    SolutionRequest,
    attempt_to_mark,
    mark_revealed,
    show_solution,
)
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.config import Config
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from tests.fakes import NOW, FakeStubGenerator, FakeToolchains, make_environment
from tests.fakes import repository_root as copy_repository

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"


@pytest.fixture
def environment(tmp_path: Path):
    root = copy_repository(tmp_path, PRACTICE)
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    return make_environment(root, toolchains=toolchains)


def show(environment, **fields):
    return show_solution(environment, SolutionRequest(**{"slug": "two-sum", **fields}))


def test_overview_is_the_explanation_table(environment):
    assert str(show(environment).overview).startswith("| Approach | Role |")


def test_default_approach_is_the_first_optimal(environment):
    assert [part.approach.id for part in show(environment).approaches] == ["hash-map"]


def test_all_shows_every_approach_in_ladder_order(environment):
    view = show(environment, all_approaches=True)
    assert [part.approach.id for part in view.approaches] == ["brute-force", "hash-map"]


def test_chosen_approach(environment):
    assert show(environment, approach_id="brute-force").approaches[0].approach.id == "brute-force"


def test_unknown_approach_is_a_usage_error(environment):
    with pytest.raises(UsageError, match="brute-force, hash-map"):
        show(environment, approach_id="greedy")


def test_approach_shows_its_explanation_section(environment):
    explanation = show(environment).approaches[0].explanation
    assert str(explanation).startswith("## Approach: hash-map (One-pass hash map)")


def test_explanation_section_stops_at_the_next_approach(environment):
    view = show(environment, approach_id="brute-force")
    assert "hash-map" not in str(view.approaches[0].explanation)


def test_approach_shows_its_code_in_the_language(environment):
    assert str(show(environment).approaches[0].code).startswith("def two_sum(")


def test_language_defaults_to_the_config(environment):
    environment = replace(environment, config=Config(default_lang=Language.KOTLIN))
    assert show(environment).language is Language.KOTLIN


def test_missing_language_lists_the_available_ones(environment):
    part = show(environment, language=Language.JAVA).approaches[0]
    assert (part.code, part.available) == (None, (Language.PYTHON,))


def test_explanation_only_shows_no_code(environment):
    assert show(environment, explanation_only=True).approaches[0].code is None


def test_language_defaults_to_the_attempt_in_progress(environment):
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    environment = replace(environment, config=Config(default_lang=Language.KOTLIN))
    assert show(environment).language is Language.PYTHON


def test_unsolved_attempt_is_marked_on_reveal(environment):
    start_attempt(environment, StartRequest("two-sum"))
    attempt = attempt_to_mark(environment, "two-sum")
    assert attempt is not None
    mark_revealed(environment, attempt)
    revealed = environment.progress.active_attempt("two-sum")
    assert revealed is not None
    assert revealed.solution_revealed


def test_passed_attempt_needs_no_confirmation(environment):
    attempt = start_attempt(environment, StartRequest("two-sum")).attempt
    environment.progress.update_attempt(replace(attempt, first_pass_at=NOW))
    assert attempt_to_mark(environment, "two-sum") is None


def test_no_attempt_needs_no_confirmation(environment):
    assert attempt_to_mark(environment, "two-sum") is None


def test_problem_without_explanation(environment):
    (environment.root / "problems/0001-two-sum/solutions/explanation.md").unlink()
    assert show(environment).approaches[0].explanation is None
