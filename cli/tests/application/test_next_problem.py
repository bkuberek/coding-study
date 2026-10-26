from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from coding_study.application.next_problem import NextRequest, next_problem
from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.config import Config, NextSettings
from coding_study.domain.next_selection import NewPick, NextSource, ReviewPick
from coding_study.domain.problem import Language, Track
from coding_study.domain.scheduling import ReviewState, ScheduleEntry
from tests.fakes import NOW, make_environment
from tests.fakes import repository_root as copy_repository
from tests.helpers import FIRST_CATALOG, copy_catalog_problems


@pytest.fixture
def problems(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return copy_catalog_problems(tmp_path_factory.mktemp("catalog"), FIRST_CATALOG)


@pytest.fixture
def environment(tmp_path: Path, problems: Path):
    return make_environment(copy_repository(tmp_path, problems))


def picked(environment, **fields) -> str | None:
    result = next_problem(environment, NextRequest(**fields))
    return result.candidate.slug if result is not None else None


def finish(environment, slug: str, grade: Grade, due_in_days: int, interval: int = 3) -> None:
    progress = environment.progress
    attempt = progress.add_attempt(NewAttempt(slug, Language.PYTHON, AttemptMode.NEW, NOW))
    status = AttemptStatus.PASSED if grade > Grade.AGAIN else AttemptStatus.FAILED
    progress.update_attempt(replace(attempt, status=status, ended_at=NOW, grade=grade))
    state = ReviewState(interval_days=interval, reps=1)
    due_on = NOW.date() + timedelta(days=due_in_days)
    progress.save_schedule_entry(ScheduleEntry(slug, state, due_on, grade, NOW))


def test_starts_with_the_first_pattern_of_the_taxonomy(environment):
    assert picked(environment) == "two-sum"


def test_a_new_pick_names_the_weakest_group(environment):
    result = next_problem(environment, NextRequest())
    assert isinstance(result, NewPick)
    assert (result.group.name, float(result.weakness)) == ("arrays-hashing", 0.75)


def test_rotates_to_an_untouched_pattern_after_a_pass(environment):
    finish(environment, "two-sum", Grade.OK, due_in_days=3)
    assert picked(environment) == "lru-cache"


def test_a_due_review_comes_first(environment):
    finish(environment, "invert-binary-tree", Grade.OK, due_in_days=0)
    result = next_problem(environment, NextRequest())
    assert isinstance(result, ReviewPick)
    assert result.candidate.slug == "invert-binary-tree"


def test_new_only_skips_the_review(environment):
    finish(environment, "invert-binary-tree", Grade.OK, due_in_days=0)
    assert picked(environment, source=NextSource.NEW_ONLY) == "two-sum"


def test_a_problem_in_progress_is_skipped(environment):
    environment.progress.add_attempt(NewAttempt("two-sum", Language.PYTHON, AttemptMode.NEW, NOW))
    assert picked(environment) == "lru-cache"


def test_scope_defaults_to_the_configured_tracks(tmp_path, problems):
    config = Config(next=NextSettings(tracks=(Track.PRACTICAL,)))
    environment = make_environment(copy_repository(tmp_path, problems), config=config)
    assert picked(environment) is None


def test_tracks_given_replace_the_configured_ones(tmp_path, problems):
    config = Config(next=NextSettings(tracks=(Track.PRACTICAL,)))
    environment = make_environment(copy_repository(tmp_path, problems), config=config)
    assert picked(environment, tracks=(Track.DSA,)) == "two-sum"


def test_the_pattern_filter(environment):
    assert picked(environment, pattern="trees") == "invert-binary-tree"


def test_the_same_snapshot_gives_the_same_pick(environment):
    finish(environment, "two-sum", Grade.AGAIN, due_in_days=1, interval=1)
    finish(environment, "invert-binary-tree", Grade.OK, due_in_days=-2)
    request = NextRequest()
    assert next_problem(environment, request) == next_problem(environment, request)
