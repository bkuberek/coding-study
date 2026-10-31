"""`cstudy solution` on a project problem: its one approach, then the reference as an overlay on
the starter (docs/specs/cli.md#cstudy-solution)."""

import pytest

from coding_study.application.environment import Environment
from coding_study.application.reveal_solution import SolutionRequest, show_solution
from coding_study.domain.config import Config
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment


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
