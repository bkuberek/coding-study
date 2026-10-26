"""Optional time limits (docs/specs/performance-analysis.md#time-limits): values, calibration
results and the limit of each case."""

import re
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

MILLISECONDS_PER_SECOND = 1000
NANOSECONDS_PER_MILLISECOND = 1_000_000

_TIME_LIMIT_PATTERN = re.compile(r"(?P<number>\d+(?:\.\d+)?)(?P<unit>x|ms|s)?")


@dataclass(frozen=True, slots=True)
class FactorTimeLimit:
    """Per case: `factor` times the calibrated reference time (subject to the floor)."""

    factor: float

    def __str__(self) -> str:
        return f"{self.factor:g}x"


@dataclass(frozen=True, slots=True)
class AbsoluteTimeLimit:
    """The same limit for every case."""

    ms: float

    def __str__(self) -> str:
        return f"{self.ms:g}ms"


type TimeLimit = FactorTimeLimit | AbsoluteTimeLimit

DEFAULT_TIME_LIMIT = FactorTimeLimit(5)


def parse_time_limit(text: str) -> TimeLimit:
    """Parse `5x` or `5` (factor), `1500ms` or `1.5s` (absolute)."""
    parsed = _TIME_LIMIT_PATTERN.fullmatch(text)
    if parsed is None or float(parsed["number"]) == 0:
        raise ValueError(
            f'invalid time limit "{text}": use a positive factor such as 5x '
            "or a duration such as 1500ms or 1.5s"
        )
    number = float(parsed["number"])
    match parsed["unit"]:
        case "ms":
            return AbsoluteTimeLimit(number)
        case "s":
            return AbsoluteTimeLimit(number * MILLISECONDS_PER_SECOND)
        case _:
            return FactorTimeLimit(number)


@dataclass(frozen=True, slots=True)
class Calibration:
    """Per-case median `duration_ns` of the fastest optimal reference on this machine."""

    approach_id: str
    case_ns: Mapping[str, int]


def per_case_medians(runs: Sequence[Mapping[str, int]]) -> dict[str, int]:
    """The median duration of each case over the runs that measured it."""
    durations: dict[str, list[int]] = {}
    for run in runs:
        for case_id, duration in run.items():
            durations.setdefault(case_id, []).append(duration)
    return {case_id: round(statistics.median(values)) for case_id, values in durations.items()}


def fastest_calibration(medians: Mapping[str, Mapping[str, int]]) -> Calibration | None:
    """The approach with the smallest total over the cases every approach measured; the first
    approach wins a tie."""
    if not medians:
        return None
    shared = frozenset[str].intersection(*(frozenset(case_ns) for case_ns in medians.values()))

    def total(approach_id: str) -> int:
        return sum(medians[approach_id][case_id] for case_id in shared)

    fastest = min(medians, key=total)
    return Calibration(fastest, dict(medians[fastest]))


@dataclass(frozen=True, slots=True)
class CaseLimit:
    ms: float
    basis: str
    """Why this limit, for reports: "5x hash-map, calibrated", "floor", or "" when absolute."""


FLOOR_BASIS = "floor"


@dataclass(frozen=True, slots=True)
class TimeLimits:
    """The time limit of each case in one run."""

    limit: TimeLimit
    floor_ms: int
    calibration: Calibration | None = None
    """Required by a factor limit."""

    def for_case(self, case_id: str) -> CaseLimit | None:
        """None when a factor limit has no calibrated time for the case."""
        if isinstance(self.limit, AbsoluteTimeLimit):
            return CaseLimit(self.limit.ms, "")
        calibration = self.calibration
        reference_ns = calibration.case_ns.get(case_id) if calibration else None
        if calibration is None or reference_ns is None:
            return None
        scaled_ms = self.limit.factor * reference_ns / NANOSECONDS_PER_MILLISECOND
        if scaled_ms < self.floor_ms:
            return CaseLimit(self.floor_ms, FLOOR_BASIS)
        return CaseLimit(scaled_ms, f"{self.limit} {calibration.approach_id}, calibrated")
