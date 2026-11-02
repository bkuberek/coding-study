"""D10, the determinism of a virtual-clock project's cases (docs/specs/authoring.md#dynamic).

`cstudy verify` grades the reference several times. A case on the virtual clock takes
microseconds to milliseconds and its only nondeterminism is the order of simultaneous wake-ups,
which Go shuffles, so a case must give the same outputs in every run, and its slowest run must stay
within a quarter of its hang guard: a correct case that creeps towards the guard would hang on a
busy machine.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from coding_study.domain.judging import CaseVerdict, Judgement, outcome_summary
from coding_study.domain.ready_criteria import MAX_SLOWEST_SHARE
from coding_study.domain.runs import Returned
from coding_study.domain.value_text import json_text

DETERMINISM_RUNS = 10
"""Runs of the reference per case."""
NS_PER_MS = 1_000_000


@dataclass(frozen=True, slots=True)
class DeterminismVerdict:
    """D10 over the runs of a reference."""

    runs: int
    agreeing: int
    """The runs that agree on the outputs of the case whose outputs differ most; every run when
    no case differs."""
    slowest_share: float | None
    """The slowest run of any case as a share of that case's hang guard; None when no run was
    measured."""
    failures: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.failures


def judge_determinism(
    runs: Sequence[Judgement], guards: Mapping[str, int], levels: Mapping[str, int | None]
) -> DeterminismVerdict:
    """The runs' verdicts compared case by case. `guards` holds each case's hang guard in
    milliseconds and `levels` its level, which names it in a failure."""
    failures: list[str] = []
    agreeing = len(runs)
    slowest: float | None = None
    for case_id in _case_ids(runs):
        verdicts = [
            verdict for run in runs for verdict in run.verdicts if verdict.case.id == case_id
        ]
        name = _name(case_id, levels)
        groups = Counter(_fingerprint(verdict) for verdict in verdicts)
        agreeing = min(agreeing, max(groups.values(), default=agreeing))
        if len(groups) > 1:
            failures.append(
                f"{name}: outputs differ between runs: {_differences(verdicts, groups)}"
            )
        share = _slowest_share(verdicts, guards[case_id])
        if share is not None:
            slowest = share if slowest is None else max(slowest, share)
        if share is not None and share > MAX_SLOWEST_SHARE:
            milliseconds = round(share * guards[case_id])
            failures.append(
                f"{name}: the slowest run took {milliseconds} ms, {share:.0%} of its hang guard "
                f"of {guards[case_id]} ms; at most {MAX_SLOWEST_SHARE:.0%}"
            )
    return DeterminismVerdict(len(runs), agreeing, slowest, tuple(failures))


def _case_ids(runs: Sequence[Judgement]) -> list[str]:
    """The cases of the runs, in the order of the first run that has them."""
    ids: dict[str, None] = {}
    for run in runs:
        ids.update(dict.fromkeys(verdict.case.id for verdict in run.verdicts))
    return list(ids)


def _name(case_id: str, levels: Mapping[str, int | None]) -> str:
    level = levels.get(case_id)
    return f"level {level} {case_id}" if level is not None else case_id


def _fingerprint(verdict: CaseVerdict) -> str:
    """What the case gave, whole: an output in full, otherwise the summary of what went wrong."""
    outcome = verdict.outcome
    if isinstance(outcome, Returned):
        return f"returned {json_text(outcome.output)}"
    return outcome_summary(outcome)


def _differences(verdicts: Sequence[CaseVerdict], groups: Counter[str]) -> str:
    """The distinct outputs, the most common first, each as the summary of its first run."""
    shown = {
        _fingerprint(verdict): outcome_summary(verdict.outcome) for verdict in reversed(verdicts)
    }
    return ", ".join(
        f"{shown[fingerprint]} in {count} of {len(verdicts)} runs"
        for fingerprint, count in groups.most_common()
    )


def _slowest_share(verdicts: Sequence[CaseVerdict], guard_ms: int) -> float | None:
    durations = [d for verdict in verdicts if (d := verdict.duration_ns) is not None]
    if not durations:
        return None
    return max(durations) / (guard_ms * NS_PER_MS)
