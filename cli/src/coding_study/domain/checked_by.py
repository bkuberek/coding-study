"""How a problem is checked, derived from its kind and its folder
(docs/specs/compatibility.md#checked-by)."""

from enum import StrEnum
from typing import assert_never

from coding_study.domain.items import EntryKind


class CheckedBy(StrEnum):
    TESTS = "tests"
    RUBRIC = "rubric"


def checked_by_of(kind: EntryKind, has_rubric: bool) -> tuple[CheckedBy, ...]:
    """`tests` for an autograded kind, `rubric` for a rubric kind or a folder with `rubric.md`, in
    that order."""
    match kind:
        case (
            EntryKind.FUNCTION
            | EntryKind.DESIGN
            | EntryKind.PROGRESSIVE
            | EntryKind.CONCURRENT
            | EntryKind.PROJECT
        ):
            return (CheckedBy.TESTS, CheckedBy.RUBRIC) if has_rubric else (CheckedBy.TESTS,)
        case EntryKind.SYSTEM_DESIGN | EntryKind.CODE_REVIEW:
            return (CheckedBy.RUBRIC,)
        case _:
            assert_never(kind)
