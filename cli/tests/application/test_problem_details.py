"""What the web UI's Problem view adds to a problem's `cstudy list` row
(docs/specs/web-ui.md#browsing)."""

from pathlib import Path

import pytest

from coding_study.application.problem_details import ITEM_DETAILS, problem_details
from coding_study.domain.errors import UnknownProblemError
from coding_study.domain.problem import ALL_LANGUAGES, Language
from tests.fakes import make_environment, repository_root
from tests.helpers import CONCURRENCY_PROBLEMS, FIXTURE_TRACKS, PROJECT_PROBLEMS

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"


@pytest.fixture
def practice(tmp_path):
    return make_environment(repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS))


@pytest.fixture
def project(tmp_path):
    return make_environment(repository_root(tmp_path, PROJECT_PROBLEMS))


@pytest.fixture
def concurrent(tmp_path):
    return make_environment(repository_root(tmp_path, CONCURRENCY_PROBLEMS))


def test_a_problem_lists_the_languages_it_can_be_started_in(practice):
    assert problem_details(practice, "two-sum").languages == ALL_LANGUAGES


def test_a_problem_lists_its_approaches(practice):
    approaches = problem_details(practice, "two-sum").approaches
    assert [(found.id, found.name, found.role) for found in approaches] == [
        ("brute-force", "Check every pair", "brute"),
        ("hash-map", "One-pass hash map", "optimal"),
    ]


def test_a_problem_counts_its_hints(practice):
    assert problem_details(practice, "two-sum").hints_total == 2


def test_a_problem_without_levels_has_no_last_level(practice):
    assert problem_details(practice, "two-sum").last_level is None


def test_a_function_problem_benches(practice):
    assert problem_details(practice, "two-sum").bench


def test_a_problem_with_a_generator_and_an_oracle_reference_takes_oracle_inputs(practice):
    assert problem_details(practice, "two-sum").oracle


def test_a_problem_without_a_generator_takes_no_oracle_inputs(practice):
    assert not problem_details(practice, "lru-cache").oracle


def test_a_problem_without_an_oracle_approach_takes_no_oracle_inputs(practice):
    meta = practice.root / "problems" / "0001-two-sum" / "meta.yaml"
    meta.write_text(meta.read_text().replace(", oracle: true", ""))
    assert not problem_details(practice, "two-sum").oracle


def test_a_project_has_its_last_level(project):
    assert problem_details(project, "bank-project-python").last_level == 2


def test_a_project_has_its_one_language(project):
    assert problem_details(project, "bank-project-python").languages == (Language.PYTHON,)


def test_a_project_does_not_bench(project):
    assert not problem_details(project, "bank-project-python").bench


def test_a_project_takes_no_oracle_inputs(project):
    assert not problem_details(project, "bank-project-python").oracle


def test_a_concurrent_problem_lists_its_broken_references(concurrent):
    assert problem_details(concurrent, "bounded-blocking-queue").broken == (
        "no-lock",
        "if-not-while",
    )


def test_a_concurrent_problem_does_not_bench(concurrent):
    assert not problem_details(concurrent, "bounded-blocking-queue").bench


def test_a_concurrent_problem_takes_no_oracle_inputs(concurrent):
    assert not problem_details(concurrent, "bounded-blocking-queue").oracle


def test_an_item_has_no_details(practice):
    assert problem_details(practice, "url-shortener") == ITEM_DETAILS


def test_an_unknown_slug_is_an_unknown_problem(practice):
    with pytest.raises(UnknownProblemError):
        problem_details(practice, "three-sum")
