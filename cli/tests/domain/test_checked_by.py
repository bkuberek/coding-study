"""How a problem is checked (docs/specs/compatibility.md#checked-by)."""

import pytest

from coding_study.domain.checked_by import CheckedBy, checked_by_of
from coding_study.domain.items import RUBRIC_KINDS, EntryKind

AUTOGRADED = [kind for kind in EntryKind if kind not in RUBRIC_KINDS]


@pytest.mark.parametrize("kind", AUTOGRADED)
def test_an_autograded_kind_is_checked_by_tests(kind):
    assert checked_by_of(kind, has_rubric=False) == (CheckedBy.TESTS,)


@pytest.mark.parametrize("kind", AUTOGRADED)
def test_an_autograded_problem_with_a_rubric_is_checked_by_tests_then_rubric(kind):
    assert checked_by_of(kind, has_rubric=True) == (CheckedBy.TESTS, CheckedBy.RUBRIC)


@pytest.mark.parametrize("kind", RUBRIC_KINDS)
@pytest.mark.parametrize("has_rubric", [True, False])
def test_a_rubric_kind_is_checked_by_its_rubric_only(kind, has_rubric):
    assert checked_by_of(kind, has_rubric) == (CheckedBy.RUBRIC,)


def test_the_values_are_tests_and_rubric():
    assert [how.value for how in CheckedBy] == ["tests", "rubric"]
