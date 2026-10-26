from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.adapters.fs_study_guides import FsStudyGuides
from coding_study.application.show_statement import ShowRequest, show_statement
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.errors import UnknownProblemError, UsageError
from coding_study.domain.problem import Language
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment
from tests.fakes import repository_root as copy_repository
from tests.helpers import FIXTURE_TRACKS

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
PHASE4 = FIXTURES / "phase4" / "problems"
PRACTICE = FIXTURES / "practice" / "problems"


def environment_on(tmp_path: Path, problems: Path):
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    return make_environment(copy_repository(tmp_path, problems), toolchains=toolchains)


@pytest.fixture
def environment(tmp_path):
    return environment_on(tmp_path, PHASE4)


def show(environment, slug="level-store", level=None) -> str:
    return show_statement(environment, ShowRequest(slug, level))


def unlock_level_2(environment) -> None:
    attempt = start_attempt(environment, StartRequest("level-store")).attempt
    environment.progress.update_attempt(replace(attempt, level_unlocked=2))


def test_shows_the_rendered_statement(environment):
    assert show(environment).startswith("# Level Store\n\nmedium · practical · level 1 of 3\n")


def test_without_an_attempt_only_level_1_shows(environment):
    assert "## Level 2" not in show(environment)


def test_shows_the_levels_the_attempt_unlocked(environment):
    unlock_level_2(environment)
    assert "## Level 2: Remove and size" in show(environment)


def test_level_shows_only_levels_up_to_it(environment):
    unlock_level_2(environment)
    assert "## Level 2" not in show(environment, level=1)


def test_a_locked_level_is_a_usage_error(environment):
    with pytest.raises(UsageError, match="level 2 is locked"):
        show(environment, level=2)


def test_never_shows_hints(environment):
    assert "Hint" not in show(environment)


def test_a_level_on_a_problem_without_levels_is_a_usage_error(tmp_path):
    environment = environment_on(tmp_path, PRACTICE)
    with pytest.raises(UsageError, match="two-sum has no levels"):
        show(environment, "two-sum", level=1)


def test_problems_without_levels_show_everything_but_hints(tmp_path):
    environment = environment_on(tmp_path, PRACTICE)
    assert "## Constraints" in show(environment, "two-sum")


def test_unknown_problem(environment):
    with pytest.raises(UnknownProblemError):
        show(environment, "nope")


@pytest.fixture
def items(tmp_path):
    return make_environment(copy_repository(tmp_path, PRACTICE, FIXTURE_TRACKS))


def test_an_item_shows_its_rendered_prompt(items):
    assert show(items, "url-shortener").startswith("# URL Shortener\n\nmedium · system-design")


def test_showing_an_item_writes_no_statement_file(items):
    show(items, "url-shortener")
    assert not items.workspace.exists(".statements/url-shortener.md")


def test_an_item_lists_the_located_study_guides(items, tmp_path):
    guides = tmp_path / "study-guides"
    guides.mkdir()
    (guides / "distributed-systems-study-guide.md").write_text("# Guide\n")
    guided = replace(items, study_guides=FsStudyGuides(guides))
    assert "## Study guides" in show(guided, "url-shortener")


def test_an_item_without_a_study_guides_root_lists_none(items):
    assert "## Study guides" not in show(items, "url-shortener")


def test_a_level_on_an_item_is_a_usage_error(items):
    with pytest.raises(UsageError, match="url-shortener has no levels"):
        show(items, "url-shortener", level=1)
