"""`cstudy list` rows for the rubric problems (docs/specs/cli.md#cstudy-list)."""

from pathlib import Path

import pytest

from coding_study.application.list_items import list_entries, list_items
from coding_study.application.list_problems import ProblemFilter
from coding_study.domain.attempts import AttemptMode, NewAttempt
from coding_study.domain.items import EntryKind
from coding_study.domain.labels import LabelFilter
from coding_study.domain.problem import Language, Track
from coding_study.domain.profile import Dimension, Profile, Widening
from coding_study.domain.scheduling import ProblemStatus
from coding_study.domain.taxonomy import Scope
from tests.fakes import NOW, make_environment, repository_root
from tests.helpers import FIXTURE_RUBRIC_PROBLEMS

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"


@pytest.fixture
def environment(tmp_path: Path):
    return make_environment(repository_root(tmp_path, PRACTICE, FIXTURE_RUBRIC_PROBLEMS))


def slugs(environment, **fields) -> list[str]:
    return [listed.meta.slug for listed in list_items(environment, ProblemFilter(**fields))]


def test_rubric_problems_follow_their_track_order(environment):
    assert slugs(environment) == ["url-shortener", "news-feed", "retry-wrapper"]


def test_a_rubric_kind_lists_the_problems_of_that_kind(environment):
    assert slugs(environment, kind=EntryKind.SYSTEM_DESIGN) == ["url-shortener", "news-feed"]
    assert slugs(environment, kind=EntryKind.CODE_REVIEW) == ["retry-wrapper"]


def test_an_autograded_kind_lists_no_rubric_problem(environment):
    assert slugs(environment, kind=EntryKind.FUNCTION) == []


def test_a_track_lists_its_items_only(environment):
    assert slugs(environment, track=Track.CODE_REVIEW) == ["retry-wrapper"]


def test_a_pattern_lists_no_item(environment):
    assert slugs(environment, pattern="arrays-hashing") == []


def test_a_domain_lists_the_items_that_name_it(environment):
    assert slugs(environment, labels=LabelFilter(domain="backend")) == [
        "url-shortener",
        "news-feed",
        "retry-wrapper",
    ]


def test_a_role_lists_the_items_that_name_it(environment):
    assert slugs(environment, labels=LabelFilter(role="platform")) == [
        "url-shortener",
        "news-feed",
    ]


def test_a_scope_lists_the_items_of_that_scope(environment):
    assert slugs(environment, labels=LabelFilter(scope=Scope.FUNCTION)) == ["retry-wrapper"]


def test_a_label_no_item_names_lists_none(environment):
    assert slugs(environment, labels=LabelFilter(domain="security")) == []


def test_an_item_with_an_attempt_in_progress_is_in_progress(environment):
    environment.progress.add_attempt(NewAttempt("url-shortener", None, AttemptMode.NEW, NOW))
    assert slugs(environment, status=ProblemStatus.IN_PROGRESS) == ["url-shortener"]


def test_the_other_items_stay_new(environment):
    environment.progress.add_attempt(NewAttempt("url-shortener", None, AttemptMode.NEW, NOW))
    assert slugs(environment, status=ProblemStatus.NEW) == ["news-feed", "retry-wrapper"]


def test_a_role_profile_keeps_the_items_that_list_a_role_of_it_and_general_ones(environment):
    assert slugs(environment, profile=Profile(job_roles=("platform",))) == [
        "url-shortener",
        "news-feed",
    ]


def test_a_language_profile_keeps_every_rubric_problem(environment):
    only_go = Profile(languages=(Language.GO,), languages_chosen=True)
    assert slugs(environment, profile=only_go) == ["url-shortener", "news-feed", "retry-wrapper"]


def test_a_domain_profile_hides_the_items_outside_it_unless_it_widens(environment):
    security = Profile(domains=("security",))
    assert slugs(environment, profile=security) == []
    widened = Widening(frozenset({Dimension.DOMAINS}))
    assert len(slugs(environment, profile=security, widening=widened)) == 3


def entries_effect(environment, **fields):
    return list_entries(environment, ProblemFilter(**fields)).profile


def test_the_effect_of_no_profile_hides_nothing(environment):
    effect = entries_effect(environment)
    assert (effect.narrowed.is_empty, effect.shown, effect.total, effect.hidden) == (True, 5, 5, 0)


def test_the_effect_counts_the_problems_and_items_the_profile_hid(environment):
    effect = entries_effect(environment, profile=Profile(job_roles=("platform",)))
    assert (effect.shown, effect.total, effect.hidden) == (4, 5, 1)
    assert effect.narrowed.job_roles == ("platform",)


def test_the_effect_counts_against_the_rows_the_other_filters_keep(environment):
    effect = entries_effect(environment, profile=Profile(domains=("backend",)), search="sum")
    assert (effect.shown, effect.total, effect.hidden) == (0, 1, 1)


def test_a_narrowing_profile_that_hides_nothing_hides_zero(environment):
    effect = entries_effect(environment, profile=Profile(domains=("backend", "algorithms")))
    assert effect.narrowed.domains == ("backend", "algorithms")
    assert effect.hidden == 0


def test_a_widened_profile_hides_nothing_and_names_nothing(environment):
    widened = Widening(frozenset(Dimension))
    effect = entries_effect(environment, profile=Profile(domains=("security",)), widening=widened)
    assert (effect.narrowed.is_empty, effect.hidden) == (True, 0)
