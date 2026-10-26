"""`cstudy solution --broken [ID]` (docs/specs/cli.md#cstudy-solution)."""

from pathlib import Path

import pytest

from coding_study.application.reveal_solution import SolutionRequest, show_solution
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from tests.fakes import make_environment, repository_root
from tests.helpers import CONCURRENCY_PROBLEMS, FIXTURE_PROBLEMS

SLUG = "bounded-blocking-queue"


@pytest.fixture
def environment(tmp_path: Path):
    return make_environment(repository_root(tmp_path, CONCURRENCY_PROBLEMS))


def broken(environment, broken_id: str = "", language: Language = Language.PYTHON, **fields):
    request = SolutionRequest(SLUG, language, broken=broken_id, **fields)
    return show_solution(environment, request).broken


def test_the_default_is_the_first_broken_reference_with_a_file(environment):
    assert broken(environment).broken.id == "no-lock"  # type: ignore[union-attr]


def test_languages_without_the_first_fall_back_to_the_next(environment):
    shown = broken(environment, language=Language.TYPESCRIPT)
    assert shown.broken.id == "if-not-while"  # type: ignore[union-attr]


def test_an_id_selects_that_broken_reference(environment):
    assert broken(environment, "if-not-while").broken.id == "if-not-while"  # type: ignore[union-attr]


def test_the_code_comes_from_solutions_broken(environment):
    code = broken(environment, "no-lock").code  # type: ignore[union-attr]
    assert "time.sleep(0)" in code  # type: ignore[operator]


def test_the_explanation_is_the_broken_section(environment):
    explanation = broken(environment, "no-lock").explanation  # type: ignore[union-attr]
    assert explanation.startswith("## Broken: no-lock (Deque without a lock)")  # type: ignore[union-attr]


def test_explanation_only_hides_the_code(environment):
    assert broken(environment, "no-lock", explanation_only=True).code is None  # type: ignore[union-attr]


def test_no_approaches_are_shown_with_broken(environment):
    view = show_solution(environment, SolutionRequest(SLUG, Language.PYTHON, broken=""))
    assert view.approaches == ()


def test_an_unknown_id_is_a_usage_error(environment):
    with pytest.raises(UsageError, match='no broken reference "deadlock"'):
        broken(environment, "deadlock")


def test_broken_and_approach_exclude_each_other(environment):
    with pytest.raises(UsageError, match="drop --approach and --all"):
        broken(environment, approach_id="monitor")


def test_problems_without_broken_references_refuse(tmp_path):
    environment = make_environment(repository_root(tmp_path, FIXTURE_PROBLEMS))
    with pytest.raises(UsageError, match="has no broken references"):
        show_solution(environment, SolutionRequest("two-sum", Language.PYTHON, broken=""))
