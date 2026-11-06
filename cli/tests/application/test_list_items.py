"""`cstudy list` rows for the non-autograded items (docs/specs/cli.md#cstudy-list)."""

from pathlib import Path

import pytest

from coding_study.application.list_items import list_items
from coding_study.application.list_problems import ProblemFilter
from coding_study.domain.items import EntryKind
from coding_study.domain.labels import LabelFilter
from coding_study.domain.problem import Track
from coding_study.domain.taxonomy import Scope
from tests.fakes import make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"


@pytest.fixture
def environment(tmp_path: Path):
    return make_environment(repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS))


def slugs(environment, **fields) -> list[str]:
    return [listed.meta.slug for listed in list_items(environment, ProblemFilter(**fields))]


def test_items_follow_their_track_order(environment):
    assert slugs(environment) == ["url-shortener", "news-feed", "retry-wrapper"]


def test_the_item_kind_lists_every_item(environment):
    assert slugs(environment, kind=EntryKind.ITEM) == [
        "url-shortener",
        "news-feed",
        "retry-wrapper",
    ]


def test_a_kind_of_problem_lists_no_item(environment):
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
