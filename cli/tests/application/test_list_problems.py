from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from coding_study.application.list_problems import ProblemFilter, list_problems, listing_context
from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.items import EntryKind
from coding_study.domain.labels import LabelFilter
from coding_study.domain.problem import ContentStatus, Difficulty, Language, Track
from coding_study.domain.profile import NO_WIDENING, Dimension, Profile, Widening
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


def test_lists_every_problem_in_the_order_of_the_listing(environment):
    assert slugs(environment) == ["two-sum", "lru-cache"]


def test_the_listing_follows_the_track_before_the_slug(environment):
    meta = environment.root / "problems" / "two-sum" / "meta.yaml"
    meta.write_text(meta.read_text().replace("track: dsa", "track: debugging"))
    assert slugs(environment) == ["lru-cache", "two-sum"]


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


def test_a_rubric_kind_leaves_every_autograded_problem_out(environment):
    assert slugs(environment, kind=EntryKind.SYSTEM_DESIGN) == []


@pytest.mark.parametrize(
    ("kind", "lists_rubric_problems"),
    [
        (None, True),
        (EntryKind.SYSTEM_DESIGN, True),
        (EntryKind.CODE_REVIEW, True),
        (EntryKind.FUNCTION, False),
    ],
)
def test_only_no_kind_or_a_rubric_kind_lists_rubric_problems(kind, lists_rubric_problems):
    assert ProblemFilter(kind=kind).lists_rubric_problems is lists_rubric_problems


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


def profiled(environment, *, widening: Widening = NO_WIDENING, **settings) -> list[str]:
    """The slugs under a profile of the given `settings` (languages, job_roles, domains)."""
    return slugs(environment, profile=Profile(**settings), widening=widening)


def test_a_profile_that_narrows_nothing_lists_every_problem(environment):
    assert profiled(environment) == ["two-sum", "lru-cache"]


def test_a_domain_profile_keeps_the_problems_that_list_one_of_its_domains(environment):
    assert profiled(environment, domains=("backend",)) == ["lru-cache"]
    assert profiled(environment, domains=("security", "algorithms")) == ["two-sum", "lru-cache"]


def test_a_role_profile_keeps_general_problems(environment):
    assert profiled(environment, job_roles=("platform",)) == ["two-sum", "lru-cache"]
    assert profiled(environment, job_roles=("backend",)) == ["two-sum", "lru-cache"]


def test_a_language_profile_keeps_the_problems_with_a_reference_in_it(environment):
    both = (Language.PYTHON, Language.GO)
    assert profiled(environment, languages=both, languages_chosen=True) == ["two-sum", "lru-cache"]
    assert profiled(environment, languages=(Language.GO,), languages_chosen=True) == []


def test_a_problem_that_lists_no_labels_matches_every_profile(environment):
    meta = environment.root / "problems" / "two-sum" / "meta.yaml"
    unlabeled = [
        line
        for line in meta.read_text().splitlines()
        if not line.startswith(("domains:", "job_roles:"))
    ]
    meta.write_text("\n".join(unlabeled) + "\n")
    assert profiled(environment, domains=("security",)) == ["two-sum"]


def test_widening_a_dimension_drops_the_profile_in_it(environment):
    assert profiled(environment, domains=("security",)) == []
    widened = Widening(frozenset({Dimension.DOMAINS}))
    assert profiled(environment, domains=("security",), widening=widened) == [
        "two-sum",
        "lru-cache",
    ]


def test_widening_another_dimension_keeps_the_profile(environment):
    widened = Widening(frozenset({Dimension.LANGUAGES, Dimension.JOB_ROLES}))
    assert profiled(environment, domains=("backend",), widening=widened) == ["lru-cache"]


def test_the_profile_combines_with_the_other_filters(environment):
    backend = Profile(domains=("backend",))
    assert slugs(environment, profile=backend, difficulty=Difficulty.EASY) == []
    assert slugs(environment, profile=backend, search="lru") == ["lru-cache"]


def test_without_profile_is_the_filter_widen_all_leaves(environment):
    narrowed = ProblemFilter(profile=Profile(domains=("security",)), search="sum")
    assert narrowed.without_profile() == ProblemFilter(search="sum")


def test_a_filter_narrows_what_its_profile_and_widening_leave(environment):
    backend = Profile(domains=("backend",))
    widened = Widening(frozenset({Dimension.DOMAINS}))
    assert ProblemFilter().narrowed().is_empty
    assert ProblemFilter(profile=backend).narrowed().domains == ("backend",)
    assert ProblemFilter(profile=backend, widening=widened).narrowed().is_empty
