"""The language `cstudy next --start` starts a pick in (docs/specs/cli.md#cstudy-next)."""

from dataclasses import replace

from coding_study.application.next_problem import start_language
from coding_study.domain.config import Config
from coding_study.domain.next_selection import Candidate
from coding_study.domain.problem import Difficulty, Language, Track
from tests.fakes import make_environment, repository_root
from tests.helpers import FIXTURE_PROBLEMS
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment

PROJECT = Candidate(
    PROJECT_SLUG,
    Track.PRACTICAL,
    Difficulty.MEDIUM,
    (),
    1,
    languages=(Language.PYTHON,),
    project=True,
)
TWO_SUM = Candidate("two-sum", Track.DSA, Difficulty.EASY)
ITEM = Candidate("url-shortener", Track.SYSTEM_DESIGN, Difficulty.MEDIUM, autograded=False)
KOTLIN = Config(default_lang=Language.KOTLIN)


def test_a_project_problem_starts_in_its_own_language(tmp_path):
    environment = project_environment(tmp_path, ScriptedProjectProcess(), config=KOTLIN)
    assert start_language(environment, PROJECT, None) is Language.PYTHON


def test_a_problem_starts_in_the_default_language(tmp_path):
    environment = make_environment(repository_root(tmp_path, FIXTURE_PROBLEMS), config=KOTLIN)
    assert start_language(environment, TWO_SUM, None) is Language.KOTLIN


def test_lang_chooses_a_problems_language(tmp_path):
    environment = make_environment(repository_root(tmp_path, FIXTURE_PROBLEMS), config=KOTLIN)
    assert start_language(environment, TWO_SUM, Language.JAVA) is Language.JAVA


def test_an_item_has_no_language(tmp_path):
    environment = make_environment(repository_root(tmp_path, FIXTURE_PROBLEMS), config=KOTLIN)
    assert start_language(environment, ITEM, Language.JAVA) is None


def test_a_default_language_outside_the_workspace_gives_way_to_its_first_language(tmp_path):
    environment = make_environment(
        repository_root(tmp_path, FIXTURE_PROBLEMS),
        config=KOTLIN,
        workspace_languages=(Language.PYTHON, Language.GO),
    )
    assert start_language(environment, TWO_SUM, None) is Language.PYTHON


def test_a_default_language_of_the_workspace_stays(tmp_path):
    environment = make_environment(
        repository_root(tmp_path, FIXTURE_PROBLEMS),
        config=KOTLIN,
        workspace_languages=(Language.PYTHON, Language.KOTLIN),
    )
    assert start_language(environment, TWO_SUM, None) is Language.KOTLIN


def test_a_project_problem_keeps_its_own_language_in_any_workspace(tmp_path):
    environment = project_environment(tmp_path, ScriptedProjectProcess(), config=KOTLIN)
    narrowed = replace(environment, workspace_languages=(Language.GO,))
    assert start_language(narrowed, PROJECT, None) is Language.PYTHON


def test_a_problem_that_lacks_the_default_language_starts_in_the_first_workspace_language_it_lists(
    tmp_path,
):
    environment = make_environment(
        repository_root(tmp_path, FIXTURE_PROBLEMS),
        workspace_languages=(Language.PYTHON, Language.KOTLIN, Language.GO),
    )
    lists = replace(TWO_SUM, languages=(Language.GO, Language.KOTLIN))
    assert start_language(environment, lists, None) is Language.KOTLIN


def test_a_problem_no_workspace_language_can_start_has_no_start_language(tmp_path):
    environment = make_environment(
        repository_root(tmp_path, FIXTURE_PROBLEMS), workspace_languages=(Language.PYTHON,)
    )
    assert start_language(environment, replace(TWO_SUM, languages=(Language.GO,)), None) is None
