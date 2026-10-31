"""The language `cstudy next --start` starts a pick in (docs/specs/cli.md#cstudy-next)."""

from coding_study.application.next_problem import start_language
from coding_study.domain.config import Config
from coding_study.domain.next_selection import Candidate
from coding_study.domain.problem import Difficulty, Language, Track
from tests.fakes import make_environment, repository_root
from tests.helpers import FIXTURE_PROBLEMS
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment

PROJECT = Candidate(
    "0001", PROJECT_SLUG, Track.PRACTICAL, Difficulty.MEDIUM, (), 1, languages=(Language.PYTHON,)
)
TWO_SUM = Candidate("0001", "two-sum", Track.DSA, Difficulty.EASY)
ITEM = Candidate(None, "url-shortener", Track.SYSTEM_DESIGN, Difficulty.MEDIUM)
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
