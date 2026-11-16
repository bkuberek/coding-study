from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from coding_study.application.next_problem import (
    NextRequest,
    NothingToPick,
    Recommendation,
    next_problem,
    next_source,
    recommend,
)
from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt, RunRecord
from coding_study.domain.config import Config, NextSettings
from coding_study.domain.errors import UsageError
from coding_study.domain.items import EntryKind
from coding_study.domain.judging import Tally
from coding_study.domain.labels import LabelFilter
from coding_study.domain.next_selection import NewPick, NextSource, ResumePick, ReviewPick
from coding_study.domain.problem import Language, Track
from coding_study.domain.profile import NO_PROFILE_EFFECT, Dimension, Profile, Widening
from coding_study.domain.scheduling import ReviewState, ScheduleEntry
from tests.fakes import NOW, make_environment
from tests.fakes import repository_root as copy_repository
from tests.helpers import FIRST_CATALOG, FIXTURE_RUBRIC_PROBLEMS, copy_catalog_problems


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


@pytest.fixture
def with_items(tmp_path: Path, problems: Path):
    return make_environment(copy_repository(tmp_path, problems, FIXTURE_RUBRIC_PROBLEMS))


def test_a_label_filter_searches_every_track(with_items):
    assert picked(with_items, labels=LabelFilter(role="platform")) == "url-shortener"


def test_tracks_given_narrow_a_label_filter(with_items):
    labels = LabelFilter(role="platform")
    assert picked(with_items, tracks=(Track.DSA,), labels=labels) is None


def test_without_a_label_filter_the_configured_tracks_apply(with_items):
    assert picked(with_items, tracks=()) == "two-sum"


def test_a_label_no_entry_names_picks_nothing(with_items):
    assert picked(with_items, labels=LabelFilter(domain="security")) is None


@pytest.mark.parametrize(
    "labels", [LabelFilter(domain="no-such-domain"), LabelFilter(role="no-such-role")]
)
def test_a_label_outside_the_lists_is_a_usage_error(environment, labels):
    with pytest.raises(UsageError):
        next_problem(environment, NextRequest(labels=labels))


def test_the_pattern_filter(environment):
    assert picked(environment, pattern="trees") == "invert-binary-tree"


def test_the_same_snapshot_gives_the_same_pick(environment):
    finish(environment, "two-sum", Grade.AGAIN, due_in_days=1, interval=1)
    finish(environment, "invert-binary-tree", Grade.OK, due_in_days=-2)
    request = NextRequest()
    assert next_problem(environment, request) == next_problem(environment, request)


def described(
    recommendation: Recommendation | NothingToPick,
) -> tuple[str, EntryKind, Language | None]:
    assert isinstance(recommendation, Recommendation)
    return recommendation.title, recommendation.kind, recommendation.language


def test_a_recommendation_names_the_title_kind_and_language(environment):
    assert described(recommend(environment, NextRequest())) == (
        "Two Sum",
        EntryKind.FUNCTION,
        Language.PYTHON,
    )


def test_a_recommendation_starts_in_the_language_asked_for(environment):
    request = NextRequest(language=Language.KOTLIN)
    assert described(recommend(environment, request))[2] is Language.KOTLIN


def test_a_rubric_problem_recommendation_has_no_language(tmp_path, problems):
    environment = make_environment(copy_repository(tmp_path, problems, FIXTURE_RUBRIC_PROBLEMS))
    request = NextRequest(tracks=(Track.SYSTEM_DESIGN,))
    assert described(recommend(environment, request)) == (
        "URL Shortener",
        EntryKind.SYSTEM_DESIGN,
        None,
    )


def test_nothing_in_scope_recommends_nothing(environment):
    assert recommend(environment, NextRequest(tracks=(Track.PRACTICAL,))) == NothingToPick()


@pytest.mark.parametrize(
    ("new", "review", "source"),
    [
        (False, False, NextSource.ANY),
        (True, False, NextSource.NEW_ONLY),
        (False, True, NextSource.REVIEWS_ONLY),
    ],
)
def test_new_and_review_choose_the_source(new, review, source):
    assert next_source(new, review) is source


def test_new_and_review_together_are_a_usage_error():
    with pytest.raises(UsageError, match="--new and --review exclude each other"):
        next_source(True, True)


def open_attempt(environment, slug: str, language: Language = Language.PYTHON, started=NOW):
    return environment.progress.add_attempt(NewAttempt(slug, language, AttemptMode.NEW, started))


def recommended(environment, **fields) -> Recommendation:
    found = recommend(environment, NextRequest(**fields))
    assert isinstance(found, Recommendation)
    return found


def test_an_attempt_in_progress_is_recommended_before_a_new_problem(environment):
    attempt = open_attempt(environment, "lru-cache")
    found = recommended(environment)
    assert isinstance(found.pick, ResumePick)
    assert (found.pick.candidate.slug, found.pick.attempt.attempt_id) == ("lru-cache", attempt.id)


def test_an_attempt_in_progress_is_recommended_before_a_due_review(environment):
    finish(environment, "invert-binary-tree", Grade.OK, due_in_days=-2)
    open_attempt(environment, "lru-cache")
    assert isinstance(recommended(environment).pick, ResumePick)


def test_a_resume_names_its_title_kind_and_the_language_of_the_attempt(environment):
    open_attempt(environment, "two-sum", Language.KOTLIN)
    found = recommended(environment)
    assert (found.title, found.kind, found.language) == (
        "Two Sum",
        EntryKind.FUNCTION,
        Language.KOTLIN,
    )


def test_the_attempt_started_last_is_resumed(environment):
    open_attempt(environment, "two-sum", started=NOW)
    open_attempt(environment, "lru-cache", started=NOW + timedelta(hours=1))
    found = recommended(environment)
    assert isinstance(found.pick, ResumePick)
    assert found.pick.candidate.slug == "lru-cache"


def test_a_test_run_makes_an_attempt_the_one_used_last(environment):
    earlier = open_attempt(environment, "two-sum", started=NOW)
    open_attempt(environment, "lru-cache", started=NOW + timedelta(hours=1))
    ran_at = NOW + timedelta(hours=2)
    environment.progress.add_test_run(RunRecord(earlier.id, ran_at, "hash", Tally(1, 4), 10))
    found = recommended(environment)
    assert isinstance(found.pick, ResumePick)
    assert (found.pick.candidate.slug, found.pick.attempt.used_at) == ("two-sum", ran_at)


def test_the_other_attempts_in_progress_are_offered(environment):
    open_attempt(environment, "two-sum", started=NOW)
    open_attempt(environment, "lru-cache", started=NOW + timedelta(hours=1))
    found = recommended(environment)
    assert isinstance(found.pick, ResumePick)
    assert [other.candidate.slug for other in found.pick.others] == ["two-sum"]


def test_new_still_picks_a_new_problem_with_an_attempt_in_progress(environment):
    open_attempt(environment, "two-sum")
    found = recommended(environment, source=NextSource.NEW_ONLY)
    assert isinstance(found.pick, NewPick)


def test_review_still_picks_a_review_with_an_attempt_in_progress(environment):
    finish(environment, "invert-binary-tree", Grade.OK, due_in_days=-2)
    open_attempt(environment, "lru-cache")
    found = recommended(environment, source=NextSource.REVIEWS_ONLY)
    assert isinstance(found.pick, ReviewPick)


def test_an_attempt_in_a_track_out_of_scope_is_not_recommended(environment):
    open_attempt(environment, "lru-cache")
    found = recommend(environment, NextRequest(tracks=(Track.PRACTICAL,)))
    assert found == NothingToPick()


def test_an_attempt_aborted_is_no_longer_recommended(environment):
    attempt = open_attempt(environment, "lru-cache")
    environment.progress.update_attempt(attempt.abandoned(NOW))
    assert isinstance(recommended(environment).pick, NewPick)


def test_a_rubric_problem_in_progress_is_resumed_without_a_language(tmp_path, problems):
    environment = make_environment(copy_repository(tmp_path, problems, FIXTURE_RUBRIC_PROBLEMS))
    environment.progress.add_attempt(NewAttempt("url-shortener", None, AttemptMode.NEW, NOW))
    found = recommended(environment, tracks=(Track.SYSTEM_DESIGN,))
    assert isinstance(found.pick, ResumePick)
    assert (found.kind, found.language) == (EntryKind.SYSTEM_DESIGN, None)


def python_and_go(environment):
    return replace(environment, workspace_languages=(Language.PYTHON, Language.GO))


def test_a_lang_outside_the_workspaces_languages_is_a_usage_error(environment):
    request = NextRequest(language=Language.KOTLIN)
    with pytest.raises(UsageError) as refused:
        next_problem(python_and_go(environment), request)
    assert str(refused.value) == (
        "kotlin is not one of this workspace's languages (python, go): cstudy lang add kotlin"
    )


def test_a_recommendation_refuses_a_lang_outside_the_workspaces_languages(environment):
    with pytest.raises(UsageError, match="cstudy lang add kotlin"):
        recommend(python_and_go(environment), NextRequest(language=Language.KOTLIN))


def test_a_lang_of_the_workspace_picks_as_before(environment):
    assert picked(python_and_go(environment), language=Language.GO) == "two-sum"


def test_a_recommendation_starts_in_the_first_workspace_language_when_the_default_is_not_one(
    environment,
):
    narrowed = replace(environment, workspace_languages=(Language.KOTLIN, Language.GO))
    assert described(recommend(narrowed, NextRequest()))[2] is Language.KOTLIN


def test_a_recommendation_starts_in_the_default_language_when_the_workspace_lists_it(environment):
    narrowed = replace(
        environment,
        workspace_languages=(Language.PYTHON, Language.GO),
        config=Config(default_lang=Language.GO),
    )
    assert described(recommend(narrowed, NextRequest()))[2] is Language.GO


def edit_meta(environment, slug: str, old: str, new: str) -> None:
    meta = environment.root / "problems" / slug / "meta.yaml"
    text = meta.read_text()
    assert old in text
    meta.write_text(text.replace(old, new, 1))


def list_languages(environment, slug: str, languages: str) -> None:
    edit_meta(
        environment, slug, "estimate_minutes:", f"languages: [{languages}]\nestimate_minutes:"
    )


def test_a_recommendation_starts_in_the_first_workspace_language_the_problem_lists(environment):
    list_languages(environment, "two-sum", "go, kotlin")
    workspace = replace(
        environment, workspace_languages=(Language.PYTHON, Language.GO, Language.KOTLIN)
    )
    found = recommended(workspace)
    assert (found.pick.candidate.slug, found.language) == ("two-sum", Language.KOTLIN)


def test_a_recommendation_starts_in_the_default_language_when_the_problem_lists_it(environment):
    list_languages(environment, "two-sum", "go, python")
    assert recommended(environment).language is Language.PYTHON


def test_a_problem_no_workspace_language_can_start_is_not_picked(environment):
    list_languages(environment, "two-sum", "go")
    only_python = replace(environment, workspace_languages=(Language.PYTHON,))
    assert picked(only_python) == "lru-cache"
    assert (
        picked(replace(environment, workspace_languages=(Language.PYTHON, Language.GO)))
        == "two-sum"
    )


def test_a_rubric_problem_is_picked_in_any_workspace(tmp_path, problems):
    environment = make_environment(copy_repository(tmp_path, problems, FIXTURE_RUBRIC_PROBLEMS))
    only_go = replace(environment, workspace_languages=(Language.GO,))
    assert picked(only_go, tracks=(Track.SYSTEM_DESIGN,)) == "url-shortener"


def test_an_attempt_in_progress_resumes_though_no_workspace_language_starts_the_problem(
    environment,
):
    list_languages(environment, "two-sum", "go")
    open_attempt(environment, "two-sum", Language.GO)
    only_python = replace(environment, workspace_languages=(Language.PYTHON,))
    found = recommended(only_python)
    assert isinstance(found.pick, ResumePick)
    assert found.language is Language.GO


def backend_lru_cache(environment) -> None:
    edit_meta(environment, "lru-cache", "domains: [algorithms]", "domains: [backend]")


BACKEND = Profile(domains=("backend",))


def test_the_profile_narrows_the_pick_and_counts_what_it_left(environment):
    backend_lru_cache(environment)
    found = recommended(environment, profile=BACKEND)
    assert found.pick.candidate.slug == "lru-cache"
    assert (found.profile.shown, found.profile.total) == (1, 3)
    assert found.profile.narrowed.domains == ("backend",)


def test_no_profile_is_no_narrowing_and_no_count(environment):
    assert recommended(environment).profile == NO_PROFILE_EFFECT
    assert recommended(environment, profile=Profile()).profile == NO_PROFILE_EFFECT


def test_widening_drops_the_profile_in_that_dimension(environment):
    backend_lru_cache(environment)
    widened = Widening(frozenset({Dimension.DOMAINS}))
    found = recommended(environment, profile=BACKEND, widening=widened)
    assert (found.pick.candidate.slug, found.profile) == ("two-sum", NO_PROFILE_EFFECT)


def test_the_profile_is_what_left_nothing_when_widening_it_picks_something(environment):
    found = recommend(environment, NextRequest(profile=Profile(domains=("security",))))
    assert isinstance(found, NothingToPick)
    assert found.profile_left_nothing
    assert (found.profile.shown, found.profile.total) == (0, 3)


def test_the_profile_is_not_what_left_nothing_when_the_scope_holds_nothing_without_it(environment):
    request = NextRequest(tracks=(Track.PRACTICAL,), profile=BACKEND)
    found = recommend(environment, request)
    assert isinstance(found, NothingToPick)
    assert not found.profile_left_nothing
    assert found.profile.narrowed.domains == ("backend",)


def test_an_attempt_in_progress_outside_the_profile_is_not_resumed(environment):
    backend_lru_cache(environment)
    open_attempt(environment, "two-sum")
    found = recommended(environment, profile=BACKEND)
    assert isinstance(found.pick, NewPick)
    assert found.pick.candidate.slug == "lru-cache"


def test_a_resume_in_the_profile_leaves_its_effect_to_the_scope(environment):
    backend_lru_cache(environment)
    open_attempt(environment, "lru-cache")
    found = recommended(environment, profile=BACKEND)
    assert isinstance(found.pick, ResumePick)
    assert (found.profile.shown, found.profile.total) == (1, 3)


def test_a_role_profile_keeps_the_general_problems(environment):
    assert picked(environment, profile=Profile(job_roles=("platform",))) == "two-sum"


def test_a_language_profile_hides_a_problem_without_a_reference_in_its_languages(environment):
    list_languages(environment, "two-sum", "python")
    profile = Profile(languages=(Language.GO,), languages_chosen=True)
    workspace = replace(environment, workspace_languages=(Language.PYTHON, Language.GO))
    assert picked(workspace, profile=profile) == "lru-cache"
    widened = Widening(frozenset({Dimension.LANGUAGES}))
    request = {"profile": profile, "widening": widened, "language": Language.PYTHON}
    assert picked(workspace, **request) == "two-sum"


def test_a_label_filter_replaces_the_profile_in_its_dimension(environment):
    backend_lru_cache(environment)
    labels = LabelFilter(domain="algorithms")
    widened = Widening(frozenset({Dimension.DOMAINS}))
    request = NextRequest(labels=labels, profile=BACKEND, widening=widened)
    result = next_problem(environment, request)
    assert result is not None
    assert result.candidate.slug == "two-sum"
