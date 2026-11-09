"""Judging the answers to a burst of requests sent at once
(docs/specs/service-projects.md#parallel-cases).

Requests that race finish in any order, so the verdict counts statuses and never reads their order.
A pass finds no race and proves none.
"""

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import JsonValue
from coding_study.domain.comparators import Mismatch
from coding_study.domain.http_case import ExpectedStatus
from coding_study.domain.http_grading import (
    FAILURE_SEPARATOR,
    Answer,
    answer_outcome,
    status_matches,
)
from coding_study.domain.judging import CaseVerdict, RunnableCase
from coding_study.domain.runs import Returned


@dataclass(frozen=True, slots=True)
class BurstAnswer:
    """What a burst brought back, with what its `after` request found."""

    statuses: tuple[int, ...]
    """Each request's status, in the order the requests were written."""
    after: Answer | None = None
    duration_ns: int = 0
    """From the case's first request to its last answer."""


def statuses_failures(
    expected: Mapping[ExpectedStatus, int], statuses: Sequence[int]
) -> tuple[str, ...]:
    """Why the statuses are not the counts expected: one reason that gives both counts in full,
    since a race shows in how they differ. A status counts toward itself before its class."""
    counted = Counter(_counted_as(expected, status) for status in statuses)
    if dict(counted) == dict(expected):
        return ()
    wanted = _listed(f"{count} to answer {status}" for status, count in _in_order(expected))
    got = _listed(f"{count} answered {status}" for status, count in _in_order(Counter(statuses)))
    return (f"{len(statuses)} requests at once: expected {wanted}; {got}",)


def burst_verdict(case: RunnableCase, burst: BurstAnswer, failures: Sequence[str]) -> CaseVerdict:
    """PASS, or FAIL with every reason found. A report shows how many answered each status, and
    the answer to the `after` request."""
    outcome = _outcome(burst)
    if failures:
        mismatch = Mismatch(FAILURE_SEPARATOR.join(failures))
        return CaseVerdict(case, CaseStatus.FAIL, outcome, mismatch)
    return CaseVerdict(case, CaseStatus.PASS, outcome)


def _counted_as(expected: Mapping[ExpectedStatus, int], status: int) -> ExpectedStatus:
    if status in expected:
        return status
    classes = (key for key in expected if isinstance(key, str) and status_matches(key, status))
    return next(classes, status)


def _in_order(counts: Mapping[ExpectedStatus, int]) -> list[tuple[ExpectedStatus, int]]:
    return sorted(counts.items(), key=lambda item: str(item[0]))


def _listed(parts: Iterable[str]) -> str:
    return " and ".join(parts)


def _outcome(burst: BurstAnswer) -> Returned:
    shown: dict[str, JsonValue] = {
        "statuses": {str(status): count for status, count in _in_order(Counter(burst.statuses))}
    }
    if burst.after is not None:
        shown["after"] = answer_outcome(burst.after.response, burst.after.expected).output
    return Returned(shown, burst.duration_ns)
