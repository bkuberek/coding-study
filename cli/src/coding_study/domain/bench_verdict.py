"""Placing the user's code on the reference ladder.

Spec: docs/specs/performance-analysis.md#verdict. The comparison reference is the `optimal`
approach with the lowest median at the largest size both it and the user completed. Every verdict
carries a confidence level; there is no percentile anywhere.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from coding_study.domain.bench_stats import TargetAnalysis, duration_text, size_text
from coding_study.domain.complexity import (
    DRIFT_TOLERANCE,
    MIN_FIT_SIZES,
    MemoryBand,
    MemoryGrowth,
    Point,
    TimeGrowth,
    band_of_class,
    class_drift,
    log_log_fit,
)
from coding_study.domain.problem import Approach

OPTIMAL_RATIO = 1.5
"""Same band and at most this much slower: optimal."""
RATIO_TREND_LIMIT = 0.1
"""A trend of 0.1 means the ratio grows about 26% per decade of n."""
HIGH_FIT_SIZES = 4
HIGH_R2 = 0.98
MEDIUM_R2 = 0.95
HIGH_SPREAD = 0.10
MEDIUM_SPREAD = 0.25
FACTOR_DECIMALS_BELOW = 10
"""Factors below this print with one decimal."""
NOT_ENOUGH_DATA = "not enough data: increase --sizes or reps"
NO_OPTIMAL = "no optimal reference ran in this language"
BEATS_OPTIMAL = "beats declared optimal: check references"


class Verdict(StrEnum):
    OPTIMAL = "optimal"
    NEAR_OPTIMAL = "near-optimal"
    SUBOPTIMAL = "suboptimal"
    UNKNOWN = "unknown"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    def at_most(self, cap: "Confidence") -> "Confidence":
        order = tuple(Confidence)
        return max(self, cap, key=order.index)


@dataclass(frozen=True, slots=True)
class Ladder:
    """The references measured in this run; `optimal_ids` are the declared `optimal` ones."""

    references: tuple[TargetAnalysis, ...]
    optimal_ids: frozenset[str]

    @property
    def optimal(self) -> tuple[TargetAnalysis, ...]:
        return tuple(ref for ref in self.references if ref.target_id in self.optimal_ids)


@dataclass(frozen=True, slots=True)
class Conditions:
    environment_warned: bool = False
    """On battery or a busy machine: confidence is capped at medium."""
    memory_cap: Confidence = Confidence.HIGH
    """The runtime's cap on memory verdicts (Node low, JVM medium)."""


@dataclass(frozen=True, slots=True)
class GrowthVerdict:
    verdict: Verdict
    message: str
    confidence: Confidence
    reference_id: str | None = None
    ratio: float | None = None
    """User median over reference median at `ratio_size`, the largest common usable size."""
    ratio_size: int | None = None
    trend: float | None = None
    warning: str | None = None


@dataclass(frozen=True, slots=True)
class SpaceVerdict:
    band: MemoryBand | None
    message: str
    confidence: Confidence


@dataclass(frozen=True, slots=True)
class BenchVerdict:
    time: GrowthVerdict
    space: SpaceVerdict


def judge(user: TargetAnalysis, ladder: Ladder, conditions: Conditions) -> BenchVerdict:
    reference = _comparison_reference(user, ladder)
    time = _TimeJudge(user, conditions.environment_warned).judge(reference)
    cap = conditions.memory_cap
    if conditions.environment_warned:
        cap = cap.at_most(Confidence.MEDIUM)
    space = _SpaceJudge(ladder, cap).judge(user, reference)
    return BenchVerdict(time, space)


def _comparison_reference(user: TargetAnalysis, ladder: Ladder) -> TargetAnalysis | None:
    """The optimal reference with the lowest median at the largest size it shares with the
    user; the first such reference in ladder order on a tie."""
    best: tuple[int, float, TargetAnalysis] | None = None
    for reference in ladder.optimal:
        common = [s for s in user.series.completed_sizes if reference.series.completed(s)]
        if not common:
            continue
        size = max(common)
        median = _median(reference, size)
        if best is None or (size, -median) > (best[0], -best[1]):
            best = (size, median, reference)
    return best[2] if best else None


class _TimeJudge:
    def __init__(self, user: TargetAnalysis, environment_warned: bool) -> None:
        self._user = user
        self._warned = environment_warned

    def judge(self, reference: TargetAnalysis | None) -> GrowthVerdict:
        """The verdict table of performance-analysis.md, evaluated in order."""
        user = self._user
        if user.time is None:
            return GrowthVerdict(Verdict.UNKNOWN, NOT_ENOUGH_DATA, Confidence.LOW)
        if reference is None:
            return GrowthVerdict(Verdict.UNKNOWN, NO_OPTIMAL, Confidence.LOW)
        over_budget = self._over_budget(reference)
        if over_budget is not None:
            return over_budget
        if reference.time is None:
            message = f"optimal reference {reference.target_id} has too few usable sizes"
            return GrowthVerdict(Verdict.UNKNOWN, message, Confidence.LOW)
        return self._by_band(user.time, reference, reference.time)

    def _over_budget(self, reference: TargetAnalysis) -> GrowthVerdict | None:
        exceeded = self._user.series.exceeded
        if exceeded is None or not reference.series.completed(exceeded.size):
            return None
        took = duration_text(_median(reference, exceeded.size))
        message = f"exceeded budget at n={size_text(exceeded.size)} where optimal took {took}"
        return self._verdict(Verdict.SUBOPTIMAL, message, reference)

    def _by_band(
        self, user_time: TimeGrowth, reference: TargetAnalysis, reference_time: TimeGrowth
    ) -> GrowthVerdict:
        if user_time.band.worse_than(reference_time.band):
            message = (
                f"growth {user_time.band.label} (slope {user_time.fit.slope:.2f}), "
                f"optimal is {reference_time.band.label}"
            )
            return self._verdict(Verdict.SUBOPTIMAL, message, reference)
        if reference_time.band.worse_than(user_time.band):
            message = f"grows slower than {reference.target_id}"
            verdict = self._verdict(Verdict.OPTIMAL, message, reference)
            return replace(verdict, warning=BEATS_OPTIMAL)
        return self._same_band(reference)

    def _same_band(self, reference: TargetAnalysis) -> GrowthVerdict:
        size, ratio = _ratio(self._user, reference)
        trend = _trend(self._user, reference)
        if ratio <= OPTIMAL_RATIO and trend < RATIO_TREND_LIMIT:
            message = f"matches {reference.target_id}, {ratio:.2f}x at n={size_text(size)}"
            verdict = Verdict.OPTIMAL
        elif trend >= RATIO_TREND_LIMIT:
            message = "same band but ratio grows with n: likely an extra log factor"
            verdict = Verdict.NEAR_OPTIMAL
        else:
            message = f"same growth, {ratio:.1f}x slower constant factor"
            verdict = Verdict.NEAR_OPTIMAL
        judged = self._verdict(verdict, message, reference)
        return replace(judged, ratio=ratio, ratio_size=size, trend=trend)

    def _verdict(self, verdict: Verdict, message: str, reference: TargetAnalysis) -> GrowthVerdict:
        confidence = _time_confidence(self._user, reference)
        if self._warned:
            confidence = confidence.at_most(Confidence.MEDIUM)
        return GrowthVerdict(verdict, message, confidence, reference.target_id)


def _time_confidence(user: TargetAnalysis, reference: TargetAnalysis) -> Confidence:
    """Fitted sizes and R^2 of both fits; spread at the user's fitted sizes, as the spec words it
    (performance-analysis.md#confidence)."""
    if user.time is None or reference.time is None:
        return Confidence.LOW
    sizes = min(len(user.time.sizes), len(reference.time.sizes))
    r2 = min(user.time.fit.r2, reference.time.fit.r2)
    spread = user.max_spread
    if sizes >= HIGH_FIT_SIZES and r2 >= HIGH_R2 and spread <= HIGH_SPREAD:
        return Confidence.HIGH
    if sizes >= MIN_FIT_SIZES and r2 >= MEDIUM_R2 and spread <= MEDIUM_SPREAD:
        return Confidence.MEDIUM
    return Confidence.LOW


def _common_usable(user: TargetAnalysis, reference: TargetAnalysis) -> list[int]:
    return [
        stats.size
        for stats in user.series.usable
        if (other := reference.series.at(stats.size)) is not None and other.usable
    ]


def _ratio(user: TargetAnalysis, reference: TargetAnalysis) -> tuple[int, float]:
    size = max(_common_usable(user, reference))
    return size, _median(user, size) / _median(reference, size)


def _trend(user: TargetAnalysis, reference: TargetAnalysis) -> float:
    """Slope of log(user / reference) against log(n) over the common usable sizes."""
    sizes = _common_usable(user, reference)
    if len(sizes) < 2:
        return 0.0
    ratios = [Point(size, _median(user, size) / _median(reference, size)) for size in sizes]
    return log_log_fit(ratios).slope


def _median(analysis: TargetAnalysis, size: int) -> float:
    """Only for sizes the target completed."""
    stats = analysis.series.at(size)
    median = stats.median_ns if stats is not None else None
    if median is None:
        raise ValueError(f"{analysis.target_id} has no median at n={size}")
    return median


class _SpaceJudge:
    def __init__(self, ladder: Ladder, cap: Confidence) -> None:
        self._ladder = ladder
        self._cap = cap

    def judge(self, user: TargetAnalysis, reference: TargetAnalysis | None) -> SpaceVerdict:
        memory = user.memory
        if memory is None:
            return SpaceVerdict(None, "space unknown: not enough memory figures", Confidence.LOW)
        confidence = _memory_confidence(memory).at_most(self._cap)
        message = f"space {memory.band}"
        if reference is None or reference.memory is None:
            return SpaceVerdict(memory.band, message, confidence)
        message += _against(memory.band, reference.target_id, reference.memory.band)
        leaner = self._leaner_alternative(memory.band, reference)
        if leaner is not None and leaner.memory is not None:
            message += f"; a {leaner.memory.band}-space optimal exists: {leaner.target_id}"
        return SpaceVerdict(memory.band, message, confidence)

    def _leaner_alternative(
        self, band: MemoryBand, reference: TargetAnalysis
    ) -> TargetAnalysis | None:
        """The leanest other reference in the comparison reference's time band, when it beats
        both the user and that reference."""
        if reference.time is None or reference.memory is None:
            return None
        candidates = [
            other
            for other in self._ladder.references
            if other.target_id != reference.target_id
            and other.time is not None
            and other.time.band is reference.time.band
            and other.memory is not None
            and band.worse_than(other.memory.band)
            and reference.memory.band.worse_than(other.memory.band)
        ]
        return min(candidates, key=_memory_rank, default=None)


def _against(band: MemoryBand, reference_id: str, reference_band: MemoryBand) -> str:
    if band is reference_band:
        return f", same as {reference_id}"
    if reference_band.worse_than(band):
        return f", less than {reference_id} ({reference_band})"
    return f", {reference_id} is {reference_band}"


def _memory_rank(analysis: TargetAnalysis) -> int:
    assert analysis.memory is not None
    return tuple(MemoryBand).index(analysis.memory.band)


def _memory_confidence(memory: MemoryGrowth) -> Confidence:
    if len(memory.sizes) >= HIGH_FIT_SIZES and memory.fit.r2 >= HIGH_R2:
        return Confidence.HIGH
    if len(memory.sizes) >= MIN_FIT_SIZES and memory.fit.r2 >= MEDIUM_R2:
        return Confidence.MEDIUM
    return Confidence.LOW


class LadderStatus(StrEnum):
    CONSISTENT = "consistent"
    TOLERATED = "tolerated"
    """The band differs, but the declared class explains the times within the drift tolerance."""
    CONTRADICTS = "contradicts"
    UNCLASSIFIED = "unclassified"


@dataclass(frozen=True, slots=True)
class LadderCheck:
    """`cstudy verify --ladder` for one reference: measured time band against `time_class`."""

    approach_id: str
    status: LadderStatus
    message: str


def check_ladder(approach: Approach, analysis: TargetAnalysis) -> LadderCheck:
    """The measured band against `time_class`; a different band contradicts the class only when
    the class, plus a fixed per-call cost, cannot explain the times within DRIFT_TOLERANCE."""
    time = analysis.time
    if approach.time_class is None:
        message = f"{approach.id} declares no time_class"
        return LadderCheck(approach.id, LadderStatus.UNCLASSIFIED, message)
    if time is None:
        usable = len(analysis.series.usable)
        exceeded = analysis.series.exceeded
        why = f" (budget exceeded at n={size_text(exceeded.size)})" if exceeded else ""
        message = (
            f"{approach.id}: {usable} usable sizes{why}; "
            "add smaller sizes to perf.size_ladder to classify it"
        )
        return LadderCheck(approach.id, LadderStatus.UNCLASSIFIED, message)
    measured = f"{time.band.label} (slope {time.fit.slope:.2f})"
    declared = approach.time_class
    if time.band is band_of_class(declared):
        return LadderCheck(approach.id, LadderStatus.CONSISTENT, f"{approach.id} {measured}")
    drift = class_drift(time.points, declared)
    tolerance = f"{DRIFT_TOLERANCE:g}x"
    if drift is not None and drift <= DRIFT_TOLERANCE:
        message = (
            f"{approach.id} declares O({declared}) and measures {measured}, but time / {declared} "
            f"varies only {_factor_text(drift)}, within the {tolerance} tolerance"
        )
        return LadderCheck(approach.id, LadderStatus.TOLERATED, message)
    message = f"{approach.id} declares O({declared}) but measures {measured}"
    if drift is not None:
        varies = f"time / {declared} varies {_excess_text(drift)}"
        message += f"; {varies}, more than the {tolerance} tolerance"
    return LadderCheck(approach.id, LadderStatus.CONTRADICTS, message)


def _factor_text(factor: float) -> str:
    """`1.3x` below 10, `50x` from 10 on."""
    return f"{factor:.1f}x" if factor < FACTOR_DECIMALS_BELOW else f"{factor:.0f}x"


def _excess_text(factor: float) -> str:
    """`_factor_text`, rounded up below 10, so a factor just over the tolerance never prints as
    the tolerance itself."""
    if factor >= FACTOR_DECIMALS_BELOW:
        return _factor_text(factor)
    return _factor_text(math.ceil(factor * 10) / 10)


@dataclass(frozen=True, slots=True)
class PastRun:
    """The user's median per call by size in an earlier bench of the same problem and language."""

    ran_at: datetime
    medians: Mapping[int, float]


@dataclass(frozen=True, slots=True)
class History:
    size: int
    best_previous_ns: float
    best_ran_at: datetime
    change: float
    """Relative to the best previous run: -0.09 is 9% faster."""
    rank: int
    """1 for the fastest run at `size`, this one included."""
    runs: int


def compare_history(current: Mapping[int, float], past: Sequence[PastRun]) -> History | None:
    """Against the best previous median at the largest size this run shares with a past run."""
    shared = [size for size in current if any(size in run.medians for run in past)]
    if not shared:
        return None
    size = max(shared)
    earlier = [run for run in past if size in run.medians]
    best = min(earlier, key=lambda run: run.medians[size])
    best_ns = best.medians[size]
    now = current[size]
    faster_runs = sum(1 for run in earlier if run.medians[size] < now)
    return History(
        size, best_ns, best.ran_at, (now - best_ns) / best_ns, faster_runs + 1, len(earlier) + 1
    )
