from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from coding_study.application.list_problems import ProblemFilter, list_problems, listing_context
from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.items import EntryKind
from coding_study.domain.labels import LabelFilter
from coding_study.domain.problem import ContentStatus, Difficulty, Language, Track
from coding_study.domain.scheduling import ProblemStatus, ReviewState, ScheduleEntry
from coding_study.domain.taxonomy import Scope
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


def test_filter_by_domain_matches_any_listed_domain(environment):
    assert slugs(environment, labels=LabelFilter(domain="backend")) == ["lru-cache"]


def test_filter_by_role_matches_any_listed_job_role(environment):
    assert slugs(environment, labels=LabelFilter(role="general")) == ["two-sum", "lru-cache"]


def test_filter_by_scope(environment):
    assert slugs(environment, labels=LabelFilter(scope=Scope.PROJECT)) == []


def test_the_label_filters_combine_by_and(environment):
    assert slugs(environment, labels=LabelFilter(domain="algorithms", role="backend")) == [
        "lru-cache"
    ]


def test_filter_by_kind(environment):
    assert slugs(environment, kind=EntryKind.DESIGN) == ["lru-cache"]


def test_the_item_kind_leaves_every_problem_out(environment):
    assert slugs(environment, kind=EntryKind.ITEM) == []


@pytest.mark.parametrize(
    ("kind", "lists_items"), [(None, True), (EntryKind.ITEM, True), (EntryKind.FUNCTION, False)]
)
def test_only_no_kind_or_the_item_kind_lists_items(kind, lists_items):
    assert ProblemFilter(kind=kind).lists_items is lists_items


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


def test_an_attempt_in_progress_makes_the_problem_in_progress(environment):
    environment.progress.add_attempt(NewAttempt("two-sum", Language.PYTHON, AttemptMode.NEW, NOW))
    assert slugs(environment, status=ProblemStatus.IN_PROGRESS) == ["two-sum"]


def test_an_attempt_in_progress_in_any_language_counts(environment):
    environment.progress.add_attempt(NewAttempt("two-sum", Language.KOTLIN, AttemptMode.NEW, NOW))
    assert slugs(environment, status=ProblemStatus.IN_PROGRESS) == ["two-sum"]


def test_a_problem_in_progress_is_no_longer_listed_as_new(environment):
    environment.progress.add_attempt(NewAttempt("two-sum", Language.PYTHON, AttemptMode.NEW, NOW))
    assert slugs(environment, status=ProblemStatus.NEW) == ["lru-cache"]


def test_an_abandoned_attempt_does_not_count(environment):
    finish(environment, AttemptStatus.ABANDONED)
    assert slugs(environment, status=ProblemStatus.IN_PROGRESS) == []


def test_a_review_attempt_in_progress_comes_ahead_of_due(environment):
    finish(environment, AttemptStatus.PASSED)
    overdue = NOW.date() - timedelta(days=1)
    environment.progress.save_schedule_entry(
        ScheduleEntry("two-sum", ReviewState(interval_days=3, reps=1), overdue, Grade.OK, NOW)
    )
    environment.progress.add_attempt(
        NewAttempt("two-sum", Language.PYTHON, AttemptMode.REVIEW, NOW)
    )
    assert slugs(environment, status=ProblemStatus.DUE) == []


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


def test_the_listing_is_of_todays_date(environment):
    assert listing_context(environment).today == NOW.date()


def test_the_listing_groups_attempts_in_progress_by_slug(environment):
    progress = environment.progress
    python = progress.add_attempt(NewAttempt("two-sum", Language.PYTHON, AttemptMode.NEW, NOW))
    later = NOW + timedelta(minutes=1)
    kotlin = progress.add_attempt(NewAttempt("two-sum", Language.KOTLIN, AttemptMode.NEW, later))
    assert listing_context(environment).in_progress == {"two-sum": (python, kotlin)}


def test_the_listing_leaves_finished_attempts_out(environment):
    finish(environment, AttemptStatus.PASSED)
    assert listing_context(environment).in_progress == {}
