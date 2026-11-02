"""`cstudy solution` on a project problem: its one approach, then the reference as an overlay on
the starter (docs/specs/cli.md#cstudy-solution)."""

import pytest

from coding_study.application.environment import Environment
from coding_study.application.reveal_solution import SolutionRequest, show_solution
from coding_study.domain.config import Config
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from tests.project_fakes import (
    PROJECT_SLUG,
    TALLY_SLUG,
    ScriptedProjectProcess,
    project_environment,
    stress_project_environment,
)


@pytest.fixture
def environment(tmp_path) -> Environment:
    config = Config(default_lang=Language.KOTLIN)
    return project_environment(tmp_path, ScriptedProjectProcess(), config=config)


def test_a_project_shows_its_own_language(environment):
    assert show_solution(environment, SolutionRequest(PROJECT_SLUG)).language is Language.PYTHON


def test_another_language_is_a_usage_error(environment):
    with pytest.raises(UsageError, match="bank-project-python is solved in python only"):
        show_solution(environment, SolutionRequest(PROJECT_SLUG, Language.JAVA))


def test_the_reference_is_the_overlay_on_the_starter(environment):
    view = show_solution(environment, SolutionRequest(PROJECT_SLUG))
    assert [(file.path, file.added) for file in view.project_files] == [("bank/bank.py", False)]


def test_the_explanation_includes_the_design(environment):
    (approach,) = show_solution(environment, SolutionRequest(PROJECT_SLUG)).approaches
    assert "### Design" in (approach.explanation or "")


def test_explanation_only_leaves_the_reference_out(environment):
    view = show_solution(environment, SolutionRequest(PROJECT_SLUG, explanation_only=True))
    assert view.project_files == ()


def test_all_shows_the_one_approach(environment):
    view = show_solution(environment, SolutionRequest(PROJECT_SLUG, all_approaches=True))
    assert [part.approach.id for part in view.approaches] == ["reference"]


# --broken on a project with stress cases (docs/specs/cli.md#cstudy-solution)


@pytest.fixture
def tally(tmp_path) -> Environment:
    return stress_project_environment(tmp_path, ScriptedProjectProcess())


def test_broken_shows_a_broken_overlay_with_its_section(tally):
    view = show_solution(tally, SolutionRequest(TALLY_SLUG, broken=""))
    broken = view.broken
    assert broken is not None
    assert (broken.broken.id, broken.available) == ("unlocked-add", (Language.PYTHON,))
    assert (broken.explanation or "").startswith("## Broken: unlocked-add (Add outside the lock)")


def test_a_broken_overlay_is_a_diff_against_the_reference(tally):
    view = show_solution(tally, SolutionRequest(TALLY_SLUG, broken="unlocked-add"))
    assert [(file.path, file.added) for file in view.project_files] == [("tally/counts.py", False)]
    (changed,) = view.project_files
    assert changed.text.startswith("--- reference/tally/counts.py\n+++ broken/tally/counts.py\n")
    assert "-        with self._lock:\n-            count = self._counts.get(key, 0) + amount" in (
        changed.text
    )


def test_broken_explanation_only_leaves_the_overlay_out(tally):
    request = SolutionRequest(TALLY_SLUG, broken="", explanation_only=True)
    assert show_solution(tally, request).project_files == ()


def test_an_unknown_broken_overlay_is_a_usage_error(tally):
    with pytest.raises(UsageError, match='no broken reference "nope" in tally-project-python'):
        show_solution(tally, SolutionRequest(TALLY_SLUG, broken="nope"))


def test_a_project_without_stress_cases_has_no_broken_references(environment):
    with pytest.raises(UsageError, match="bank-project-python has no broken references"):
        show_solution(environment, SolutionRequest(PROJECT_SLUG, broken=""))
