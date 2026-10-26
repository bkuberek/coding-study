"""Per-size statistics of a bench report and the growth fitted to them.

Spec: docs/specs/performance-analysis.md#measurement. Per target and size: the median time per
call over the repetitions, and spread = median absolute deviation / median. A size is usable for
the time fit when its samples last at least 50 microseconds (shorter, and timer resolution
dominates); fast calls are batched so that most sizes are.
"""

import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from coding_study.domain.bench_runs import SizeMeasurements, TargetReport
from coding_study.domain.complexity import (
    MemoryGrowth,
    Point,
    TimeGrowth,
    classify_memory,
    classify_time,
)
from coding_study.domain.runs import UserError

MIN_USABLE_SAMPLE_NS = 50_000
NANOSECONDS_PER_MILLISECOND = 1_000_000
NANOSECONDS_PER_MICROSECOND = 1000
SMALLEST_MILLISECONDS_NS = 9_950
"""Shorter durations print in microseconds: in milliseconds they would round to 0.00ms."""
MILLISECONDS_PER_SECOND = 1000
POWER_OF_TEN_BASE = 10


class SizeStatus(StrEnum):
    COMPLETED = "ok"
    BUDGET_EXCEEDED = "budget_exceeded"
    FAILED = "error"
    NOT_RUN = "not_run"


@dataclass(frozen=True, slots=True)
class SizeStats:
    size: int
    status: SizeStatus
    median_ns: float | None = None
    """Per call; set when the size completed."""
    spread: float | None = None
    cpu_ns: float | None = None
    calls: int | None = None
    """Calls per timed sample."""
    memory_bytes: int | None = None
    memory_metric: str | None = None
    exceeded_ns: int | None = None
    """The call that went over the budget (or the hang guard)."""

    @property
    def usable(self) -> bool:
        """Completed, with samples long enough to time reliably."""
        if self.median_ns is None or self.calls is None:
            return False
        return self.median_ns * self.calls >= MIN_USABLE_SAMPLE_NS


@dataclass(frozen=True, slots=True)
class TargetSeries:
    target_id: str
    sizes: tuple[SizeStats, ...] = ()
    load_error: UserError | None = None

    def at(self, size: int) -> SizeStats | None:
        return next((stats for stats in self.sizes if stats.size == size), None)

    def completed(self, size: int) -> bool:
        stats = self.at(size)
        return stats is not None and stats.status is SizeStatus.COMPLETED

    @property
    def completed_sizes(self) -> tuple[int, ...]:
        return tuple(stats.size for stats in self.sizes if stats.status is SizeStatus.COMPLETED)

    @property
    def usable(self) -> tuple[SizeStats, ...]:
        return tuple(stats for stats in self.sizes if stats.usable)

    @property
    def exceeded(self) -> SizeStats | None:
        """The size where the target went over the budget, if it did."""
        return next(
            (stats for stats in self.sizes if stats.status is SizeStatus.BUDGET_EXCEEDED), None
        )


@dataclass(frozen=True, slots=True)
class TargetAnalysis:
    series: TargetSeries
    time: TimeGrowth | None
    """None: fewer than three usable sizes."""
    memory: MemoryGrowth | None

    @property
    def target_id(self) -> str:
        return self.series.target_id

    @property
    def max_spread(self) -> float:
        """The largest spread among the sizes the time fit used."""
        fitted = set(self.time.sizes) if self.time else set[int]()
        spreads = [s.spread for s in self.series.sizes if s.size in fitted and s.spread is not None]
        return max(spreads, default=0.0)


def summarize(report: TargetReport) -> TargetSeries:
    return TargetSeries(
        report.target_id,
        tuple(_size_stats(measured) for measured in report.sizes),
        report.load_error,
    )


def analyze(series: TargetSeries) -> TargetAnalysis:
    time_points = [Point(s.size, s.median_ns) for s in series.usable if s.median_ns]
    memory_points = [
        Point(s.size, float(s.memory_bytes))
        for s in series.sizes
        if s.status is SizeStatus.COMPLETED and s.memory_bytes is not None
    ]
    return TargetAnalysis(series, classify_time(time_points), classify_memory(memory_points))


def size_text(size: int) -> str:
    """`1e5` for round powers of ten times a digit, else the plain number."""
    exponent = 0
    mantissa = size
    while mantissa >= POWER_OF_TEN_BASE and mantissa % POWER_OF_TEN_BASE == 0:
        mantissa //= POWER_OF_TEN_BASE
        exponent += 1
    if exponent < 2 or mantissa >= POWER_OF_TEN_BASE:
        return str(size)
    return f"{mantissa}e{exponent}"


def duration_text(nanoseconds: float) -> str:
    """`2.4µs` below 10 µs (which would read 0.00ms), then milliseconds, then seconds."""
    if nanoseconds < SMALLEST_MILLISECONDS_NS:
        return f"{nanoseconds / NANOSECONDS_PER_MICROSECOND:.1f}µs"
    milliseconds = nanoseconds / NANOSECONDS_PER_MILLISECOND
    if milliseconds < 10:
        return f"{milliseconds:.2f}ms"
    if milliseconds < 100:
        return f"{milliseconds:.1f}ms"
    if milliseconds < MILLISECONDS_PER_SECOND:
        return f"{milliseconds:.0f}ms"
    return f"{milliseconds / MILLISECONDS_PER_SECOND:.2f}s"


def _size_stats(measured: SizeMeasurements) -> SizeStats:
    memory = measured.memory
    if measured.exceeded_ns is not None:
        return SizeStats(
            measured.size, SizeStatus.BUDGET_EXCEEDED, exceeded_ns=measured.exceeded_ns
        )
    if measured.failure is not None:
        return SizeStats(measured.size, SizeStatus.FAILED)
    if not measured.samples:
        return SizeStats(measured.size, SizeStatus.NOT_RUN)
    per_call = [sample.per_call_ns for sample in measured.samples]
    median = statistics.median(per_call)
    return SizeStats(
        size=measured.size,
        status=SizeStatus.COMPLETED,
        median_ns=median,
        spread=_spread(per_call, median),
        cpu_ns=statistics.median(sample.cpu_per_call_ns for sample in measured.samples),
        calls=measured.samples[0].calls,
        memory_bytes=memory.bytes if memory else None,
        memory_metric=memory.metric if memory else None,
    )


def _spread(values: Sequence[float], median: float) -> float:
    if median == 0:
        return 0.0
    return statistics.median(abs(value - median) for value in values) / median
