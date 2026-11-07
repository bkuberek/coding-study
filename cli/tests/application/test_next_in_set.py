"""`cstudy next --set`: the set's own order (docs/specs/progress-and-scheduling.md#with---set)."""

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from coding_study.application.next_problem import (
    NextRequest,
    NothingToPick,
    Recommendation,
    next_problem,
    recommend,
)
from coding_study.application.problem_sets import add_to_set, create_set
from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.config import Config, NextSettings
from coding_study.domain.errors import UnknownSetError
from coding_study.domain.items import EntryKind
from coding_study.domain.next_selection import (
    NextSource,
    ResumePick,
    ReviewPick,
    SetPick,
)
from coding_study.domain.problem import Difficulty, Language, Track
from coding_study.domain.scheduling import ReviewState, ScheduleEntry
from tests.fakes import NOW, jdk_of, make_environment, repository_root
from tests.helpers import FIRST_CATALOG, FIXTURE_TRACKS, copy_catalog_problems

LOOP = "backend-loop"


@pytest.fixture
def environment(tmp_path: Path, tmp_path_factory: pytest.TempPathFactory):
    problems = copy_catalog_problems(tmp_path_factory.mktemp("catalog"), FIRST_CATALOG)
    environment = make_environment(repository_root(tmp_path, problems, FIXTURE_TRACKS))
    create_set(environment, LOOP)
    return environment


def in_order(environment, *slugs: str) -> None:
    add_to_set(environment, LOOP, slugs)


def finish(
    environment,
    slug: str,
    status: AttemptStatus = AttemptStatus.PASSED,
    due_in_days: int | None = None,
) -> None:
    progress = environment.progress
    attempt = progress.add_attempt(NewAttempt(slug, Language.PYTHON, AttemptMode.NEW, NOW))
    progress.update_attempt(replace(attempt, status=status, ended_at=NOW, grade=Grade.OK))
    if due_in_days is not None:
        state = ReviewState(interval_days=3, reps=1)
        due_on = NOW.date() + timedelta(days=due_in_days)
        progress.save_schedule_entry(ScheduleEntry(slug, state, due_on, Grade.OK, NOW))


def open_attempt(environment, slug: str, language: Language = Language.PYTHON) -> None:
    environment.progress.add_attempt(NewAttempt(slug, language, AttemptMode.NEW, NOW))


def recommended(environment, **fields) -> Recommendation:
    found = recommend(environment, NextRequest(set_name=LOOP, **fields))
    assert isinstance(found, Recommendation)
    return found


def picked_slug(environment, **fields) -> str:
    return recommended(environment, **fields).pick.candidate.slug


def nothing(environment, **fields) -> NothingToPick:
    found = recommend(environment, NextRequest(set_name=LOOP, **fields))
    assert isinstance(found, NothingToPick)
    return found


def test_the_set_s_order_comes_before_the_weakest_pattern(environment):
    in_order(environment, "invert-binary-tree", "two-sum")
    assert picked_slug(environment) == "invert-binary-tree"


def test_the_pick_says_where_it_is_in_the_set(environment):
    in_order(environment, "two-sum", "lru-cache")
    finish(environment, "two-sum")
    pick = recommended(environment).pick
    assert isinstance(pick, SetPick)
    assert (pick.set_name, pick.position, pick.total) == (LOOP, 2, 2)


def test_a_passed_problem_is_passed_over(environment):
    in_order(environment, "two-sum", "lru-cache")
    finish(environment, "two-sum", due_in_days=3)
    assert picked_slug(environment) == "lru-cache"


def test_a_failed_problem_is_still_the_next_one(environment):
    in_order(environment, "two-sum", "lru-cache")
    finish(environment, "two-sum", AttemptStatus.FAILED)
    assert picked_slug(environment) == "two-sum"


def test_an_abandoned_attempt_changes_nothing(environment):
    in_order(environment, "two-sum", "lru-cache")
    finish(environment, "two-sum", AttemptStatus.ABANDONED)
    assert picked_slug(environment) == "two-sum"


def test_an_open_attempt_in_the_set_comes_first(environment):
    in_order(environment, "two-sum", "lru-cache")
    open_attempt(environment, "lru-cache")
    pick = recommended(environment).pick
    assert (isinstance(pick, ResumePick), pick.candidate.slug) == (True, "lru-cache")


def test_an_open_attempt_outside_the_set_is_not_offered(environment):
    in_order(environment, "two-sum")
    open_attempt(environment, "lru-cache")
    assert picked_slug(environment) == "two-sum"


def test_the_others_open_in_the_set_are_listed(environment):
    in_order(environment, "two-sum", "lru-cache")
    open_attempt(environment, "two-sum")
    open_attempt(environment, "lru-cache")
    open_attempt(environment, "invert-binary-tree")
    pick = recommended(environment).pick
    assert isinstance(pick, ResumePick)
    assert len(pick.others) == 1


def test_a_problem_not_passed_comes_before_a_due_review(environment):
    in_order(environment, "two-sum", "lru-cache")
    finish(environment, "two-sum", due_in_days=-2)
    assert picked_slug(environment) == "lru-cache"


def test_a_due_review_follows_when_all_passed(environment):
    in_order(environment, "two-sum", "lru-cache")
    finish(environment, "two-sum", due_in_days=3)
    finish(environment, "lru-cache", due_in_days=-1)
    pick = recommended(environment).pick
    assert (isinstance(pick, ReviewPick), pick.candidate.slug) == (True, "lru-cache")


def test_a_due_review_outside_the_set_is_not_offered(environment):
    in_order(environment, "two-sum")
    finish(environment, "two-sum", due_in_days=3)
    finish(environment, "lru-cache", due_in_days=-1)
    assert nothing(environment).set_standing is not None


def test_reviews_keep_their_priority_within_the_set(environment):
    in_order(environment, "invert-binary-tree", "two-sum")
    finish(environment, "invert-binary-tree", due_in_days=-1)
    finish(environment, "two-sum", due_in_days=-9)
    assert picked_slug(environment) == "two-sum"


def test_a_set_changes_no_weakness_score(environment):
    finish(environment, "two-sum", due_in_days=-1)
    finish(environment, "lru-cache", due_in_days=-1)
    plain = next_problem(environment, NextRequest())
    in_order(environment, "two-sum", "lru-cache")
    assert isinstance(plain, ReviewPick)
    assert picked_slug(environment) == plain.candidate.slug


def test_a_set_with_nothing_left_is_finished(environment):
    in_order(environment, "two-sum")
    finish(environment, "two-sum", due_in_days=3)
    standing = nothing(environment).set_standing
    assert standing is not None
    assert (standing.finished, standing.passed, standing.total) == (True, 1, 1)


def test_an_empty_set_has_nothing_to_pick_and_is_not_finished(environment):
    standing = nothing(environment).set_standing
    assert standing is not None
    assert (standing.finished, standing.total) == (False, 0)


def test_a_set_of_slugs_the_catalog_lost_has_nothing_to_pick(tmp_path, environment):
    (tmp_path / "sets.yaml").write_text(f"sets:\n  {LOOP}:\n    problems:\n      - gone\n")
    standing = nothing(environment).set_standing
    assert standing is not None
    assert (standing.total, standing.missing) == (0, ("gone",))


def test_a_slug_the_catalog_lost_is_passed_over(tmp_path, environment):
    (tmp_path / "sets.yaml").write_text(
        f"sets:\n  {LOOP}:\n    problems:\n      - gone\n      - two-sum\n"
    )
    assert picked_slug(environment) == "two-sum"


def test_an_item_can_be_the_pick_whatever_next_tracks_says(environment):
    in_order(environment, "url-shortener")
    found = recommended(environment)
    assert (found.pick.candidate.slug, found.kind, found.language) == (
        "url-shortener",
        EntryKind.ITEM,
        None,
    )


def test_a_track_narrows_the_set(environment):
    in_order(environment, "url-shortener", "two-sum")
    assert picked_slug(environment, tracks=(Track.DSA,)) == "two-sum"


def test_a_filter_applies_within_the_set(environment):
    in_order(environment, "lru-cache", "two-sum")
    assert picked_slug(environment, difficulty=Difficulty.EASY) == "two-sum"


def test_a_filter_that_leaves_nothing_does_not_call_the_set_finished(environment):
    in_order(environment, "two-sum")
    standing = nothing(environment, difficulty=Difficulty.HARD).set_standing
    assert standing is not None
    assert standing.finished is False


def test_a_draft_of_your_own_in_the_set_can_be_picked(tmp_path, environment):
    meta = next((tmp_path / "problems").glob("*two-sum/meta.yaml"))
    meta.write_text(meta.read_text().replace("status: ready", "status: draft"))
    in_order(environment, "two-sum")
    assert picked_slug(environment) == "two-sum"


def test_new_only_skips_the_open_attempt_and_the_review(environment):
    in_order(environment, "two-sum", "lru-cache", "invert-binary-tree")
    open_attempt(environment, "two-sum")
    finish(environment, "lru-cache", due_in_days=-1)
    assert picked_slug(environment, source=NextSource.NEW_ONLY) == "invert-binary-tree"


def test_reviews_only_skips_the_order(environment):
    in_order(environment, "two-sum", "lru-cache")
    finish(environment, "lru-cache", due_in_days=-1)
    assert picked_slug(environment, source=NextSource.REVIEWS_ONLY) == "lru-cache"


def test_reviews_only_with_none_due_has_nothing_to_pick(environment):
    in_order(environment, "two-sum")
    assert nothing(environment, source=NextSource.REVIEWS_ONLY).set_standing is not None


def test_a_problem_the_jdk_cannot_run_is_passed_over(tmp_path, tmp_path_factory):
    problems = copy_catalog_problems(tmp_path_factory.mktemp("catalog"), FIRST_CATALOG)
    environment = make_environment(
        repository_root(tmp_path, problems, FIXTURE_TRACKS),
        config=Config(default_lang=Language.JAVA),
        jdk=jdk_of(27),
    )
    create_set(environment, LOOP)
    in_order(environment, "two-sum", "url-shortener")
    assert picked_slug(environment) == "url-shortener"


def test_when_the_jdk_left_nothing_it_says_why(tmp_path, tmp_path_factory):
    problems = copy_catalog_problems(tmp_path_factory.mktemp("catalog"), FIRST_CATALOG)
    environment = make_environment(
        repository_root(tmp_path, problems, FIXTURE_TRACKS),
        config=Config(default_lang=Language.JAVA),
        jdk=jdk_of(27),
    )
    create_set(environment, LOOP)
    in_order(environment, "two-sum")
    assert "JDK 27" in (nothing(environment).jdk_reason or "")


def test_the_jdk_is_not_blamed_for_what_is_outside_the_set(tmp_path, tmp_path_factory):
    problems = copy_catalog_problems(tmp_path_factory.mktemp("catalog"), FIRST_CATALOG)
    environment = make_environment(
        repository_root(tmp_path, problems, FIXTURE_TRACKS),
        config=Config(default_lang=Language.JAVA),
        jdk=jdk_of(27),
    )
    create_set(environment, LOOP)
    in_order(environment, "url-shortener")
    finish(environment, "url-shortener", due_in_days=3)
    assert nothing(environment).jdk_reason is None


def test_an_unknown_set_is_refused(environment):
    with pytest.raises(UnknownSetError):
        recommend(environment, NextRequest(set_name="nope"))


def test_without_a_set_the_standing_is_absent(tmp_path, tmp_path_factory):
    problems = copy_catalog_problems(tmp_path_factory.mktemp("catalog"), FIRST_CATALOG)
    config = Config(next=NextSettings(tracks=(Track.PRACTICAL,)))
    environment = make_environment(repository_root(tmp_path, problems), config=config)
    found = recommend(environment, NextRequest())
    assert isinstance(found, NothingToPick)
    assert found.set_standing is None


def test_a_recommendation_without_a_set_has_no_standing(environment):
    found = recommend(environment, NextRequest())
    assert isinstance(found, Recommendation)
    assert found.set_standing is None


def test_a_recommendation_in_a_set_has_its_standing(environment):
    in_order(environment, "two-sum", "lru-cache")
    finish(environment, "two-sum")
    standing = recommended(environment).set_standing
    assert standing is not None
    assert (standing.name, standing.passed, standing.total) == (LOOP, 1, 2)
