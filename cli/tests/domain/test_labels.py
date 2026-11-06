import pytest

from coding_study.domain.labels import LabelFilter, Labels
from coding_study.domain.taxonomy import Scope

LABELS = Labels(
    domains=("backend", "fintech"), job_roles=("backend", "platform"), scope=Scope.PROJECT
)


def test_an_empty_filter_is_not_set():
    assert LabelFilter().is_set is False


@pytest.mark.parametrize(
    "label_filter",
    [LabelFilter(domain="backend"), LabelFilter(role="backend"), LabelFilter(scope=Scope.SYSTEM)],
)
def test_a_filter_with_any_field_is_set(label_filter):
    assert label_filter.is_set is True


def test_an_empty_filter_matches_labels_that_are_not_there():
    assert LabelFilter().matches(Labels()) is True


@pytest.mark.parametrize("domain", ["backend", "fintech"])
def test_the_domain_matches_any_listed_domain(domain):
    assert LabelFilter(domain=domain).matches(LABELS) is True


def test_the_domain_does_not_match_an_unlisted_domain():
    assert LabelFilter(domain="security").matches(LABELS) is False


@pytest.mark.parametrize("role", ["backend", "platform"])
def test_the_role_matches_any_listed_job_role(role):
    assert LabelFilter(role=role).matches(LABELS) is True


def test_the_role_does_not_match_an_unlisted_job_role():
    assert LabelFilter(role="general").matches(LABELS) is False


def test_the_scope_matches_the_scope():
    assert LabelFilter(scope=Scope.PROJECT).matches(LABELS) is True


def test_the_scope_does_not_match_another_scope():
    assert LabelFilter(scope=Scope.FUNCTION).matches(LABELS) is False


def test_every_set_field_must_match():
    assert LabelFilter(domain="backend", role="general").matches(LABELS) is False


@pytest.mark.parametrize(
    "label_filter",
    [LabelFilter(domain="backend"), LabelFilter(role="backend"), LabelFilter(scope=Scope.FUNCTION)],
)
def test_labels_that_are_not_there_match_no_set_field(label_filter):
    assert label_filter.matches(Labels()) is False
