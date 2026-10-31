from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from coding_study.application.list_problems import ProblemFilter, list_problems
from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.problem import ContentStatus, Difficulty, Language, Track
from coding_study.domain.scheduling import ProblemStatus, ReviewState, ScheduleEntry
from tests.fakes import NOW, make_environment
from tests.fakes import repository_root as copy_repository
from tests.helpers import PROJECT_PROBLEMS

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"


@pytest.fixture
def environment(tmp_path: Path):
    return make_environment(copy_repository(tmp_path, PRACTICE))


def slugs(environment, **fields) -> list[str]:
    return [
        listed.summary.meta.slug for listed in list_problems(environment, ProblemFilter(**fields))
    ]


def test_lists_every_problem_in_id_order(environment):
    assert slugs(environment) == ["two-sum", "lru-cache"]


def test_untouched_problems_are_new(environment):
    assert {listed.status for listed in list_problems(environment, ProblemFilter())} == {
        ProblemStatus.NEW
    }


def test_filter_by_difficulty(environment):
    assert slugs(environment, difficulty=Difficulty.MEDIUM) == ["lru-cache"]


def test_filter_by_pattern_matches_any_listed_pattern(environment):
    assert slugs(environment, pattern="linked-list") == ["lru-cache"]


def test_filter_by_track(environment):
    assert slugs(environment, track=Track.LLD) == []


def test_filter_by_content_status(environment):
    assert slugs(environment, content=ContentStatus.DRAFT) == ["lru-cache"]


def test_filter_by_reference_language(environment):
    assert slugs(environment, language=Language.PYTHON) == ["two-sum", "lru-cache"]


def test_filter_by_language_without_references(environment):
    assert slugs(environment, language=Language.KOTLIN) == []


@pytest.mark.parametrize(
    ("language", "listed"),
    [(Language.PYTHON, ["bank-project-python"]), (Language.TYPESCRIPT, [])],
)
def test_a_project_is_listed_under_the_language_of_its_overlay(tmp_path, language, listed):
    environment = make_environment(copy_repository(tmp_path, PROJECT_PROBLEMS))
    assert slugs(environment, language=language) == listed


def finish(environment, status: AttemptStatus) -> None:
    attempt = environment.progress.add_attempt(
        NewAttempt("two-sum", Language.PYTHON, AttemptMode.NEW, NOW)
    )
    environment.progress.update_attempt(replace(attempt, status=status))


def test_status_comes_from_progress(environment):
    finish(environment, AttemptStatus.FAILED)
    assert slugs(environment, status=ProblemStatus.ATTEMPTED) == ["two-sum"]


def test_due_date_comes_from_the_schedule(environment):
    finish(environment, AttemptStatus.PASSED)
    due = date(2026, 10, 27)
    environment.progress.save_schedule_entry(
        ScheduleEntry("two-sum", ReviewState(interval_days=3, reps=1), due, Grade.OK, NOW)
    )
    assert list_problems(environment, ProblemFilter())[0].due_on == due


def test_overdue_problems_are_due(environment):
    finish(environment, AttemptStatus.PASSED)
    overdue = NOW.date() - timedelta(days=1)
    environment.progress.save_schedule_entry(
        ScheduleEntry("two-sum", ReviewState(interval_days=3, reps=1), overdue, Grade.OK, NOW)
    )
    assert slugs(environment, status=ProblemStatus.DUE) == ["two-sum"]
