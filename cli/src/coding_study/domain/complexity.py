"""Empirical growth classes from measurements at several sizes.

Spec: docs/specs/performance-analysis.md#empirical-classification. A least-squares fit of
`log(value) = a + b * log(n)` gives the slope `b`; coarse bands of `b` stand for the declared
complexity classes. n and n log n share a band: over practical sizes the log factor adds only
about 0.1 to the slope, less than the noise. The sublinear classes 1, log n and sqrt n share one
too: each call reads a fresh copy of its input, so memory-system effects, not the operation
count, dominate the nanoseconds to microseconds such a call takes.

The drift of a declared class (ADR 0009) asks the converse question for `cstudy verify --ladder`:
can that class, plus a fixed per-call cost, explain the times within the factor by which the
cost per unit of growth wanders across a ladder (cache levels, load, inputs)?
"""

import itertools
import math
import statistics
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from coding_study.domain.problem import ComplexityClass

MIN_FIT_SIZES = 3
DRIFT_TOLERANCE = 4.0
"""How much the cost per unit of a class may vary across a ladder before the class no longer
explains the times: cache levels, background load and the per-seed choice of inputs move it by
up to about this factor on references whose class is known (ADR 0009)."""
CONSTANT_MEMORY_BYTES = 4096
"""Memory figures below this count as this much, so small allocations read as constant."""


@dataclass(frozen=True, slots=True)
class Point:
    size: int
    value: float
    """Nanoseconds per call or bytes; always positive."""


@dataclass(frozen=True, slots=True)
class LogFit:
    slope: float
    intercept: float
    r2: float


def log_log_fit(points: Sequence[Point]) -> LogFit:
    """Fit of `log(value)` against `log(size)`; raises ValueError for fewer than two sizes."""
    return _least_squares([math.log(p.size) for p in points], [math.log(p.value) for p in points])


def semi_log_fit(points: Sequence[Point]) -> LogFit:
    """Fit of `log(value)` against `size`; an exponential is a straight line here."""
    return _least_squares([float(p.size) for p in points], [math.log(p.value) for p in points])


class TimeBand(StrEnum):
    """Slope bands in growth order (performance-analysis.md#time); X is exponential."""

    A = "A"
    """Sublinear: constant, logarithmic and square-root growth are not separable."""
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    X = "X"
    """Exponential, or steeper than any declared polynomial class (3.4 and above)."""

    def worse_than(self, other: "TimeBand") -> bool:
        return _TIME_ORDER.index(self) > _TIME_ORDER.index(other)

    @property
    def label(self) -> str:
        return _TIME_BANDS[self].label

    @property
    def classes(self) -> tuple[ComplexityClass, ...]:
        """The declared classes this band stands for; none for the bands between classes."""
        return _TIME_BANDS[self].classes


@dataclass(frozen=True, slots=True)
class _BandSpec:
    upper: float
    """The band holds slopes below this and at or above the previous band's upper bound."""
    label: str
    classes: tuple[ComplexityClass, ...] = ()


_TIME_BANDS: dict[TimeBand, _BandSpec] = {
    TimeBand.A: _BandSpec(
        0.75,
        "~1|log n|sqrt n",
        (ComplexityClass.CONSTANT, ComplexityClass.LOGARITHMIC, ComplexityClass.SQUARE_ROOT),
    ),
    TimeBand.C: _BandSpec(1.35, "~n|nlogn", (ComplexityClass.LINEAR, ComplexityClass.LINEARITHMIC)),
    TimeBand.D: _BandSpec(1.75, "~n^1.5"),
    TimeBand.E: _BandSpec(
        2.35, "~n^2", (ComplexityClass.QUADRATIC, ComplexityClass.QUADRATIC_LOGARITHMIC)
    ),
    TimeBand.F: _BandSpec(2.75, "~n^2.5"),
    TimeBand.G: _BandSpec(3.4, "~n^3", (ComplexityClass.CUBIC,)),
    TimeBand.X: _BandSpec(
        math.inf, "~2^n", (ComplexityClass.EXPONENTIAL, ComplexityClass.FACTORIAL)
    ),
}
_TIME_ORDER = tuple(TimeBand)
_POLYNOMIAL_CEILING = _TIME_BANDS[TimeBand.G].upper
"""Steeper than the cubic band: `a + b * n^k` (a, b >= 0) never has a local slope above k, so a
local slope at or above this cannot come from a declared polynomial class plus a fixed cost."""


def time_band_of_slope(slope: float) -> TimeBand:
    """The band of a log-log slope; X from the polynomial ceiling on."""
    return next(band for band in _TIME_ORDER if slope < _TIME_BANDS[band].upper)


def band_of_class(declared: ComplexityClass) -> TimeBand:
    return next(band for band in _TIME_ORDER if declared in _TIME_BANDS[band].classes)


class MemoryBand(StrEnum):
    CONSTANT = "constant"
    SUBLINEAR = "sublinear"
    LINEAR = "linear"
    SUPERLINEAR = "superlinear"

    def worse_than(self, other: "MemoryBand") -> bool:
        return _MEMORY_ORDER.index(self) > _MEMORY_ORDER.index(other)


_MEMORY_UPPER_SLOPES = {
    MemoryBand.CONSTANT: 0.3,
    MemoryBand.SUBLINEAR: 0.75,
    MemoryBand.LINEAR: 1.35,
    MemoryBand.SUPERLINEAR: math.inf,
}
_MEMORY_ORDER = tuple(MemoryBand)


def memory_band_of_slope(slope: float) -> MemoryBand:
    return next(band for band in _MEMORY_ORDER if slope < _MEMORY_UPPER_SLOPES[band])


@dataclass(frozen=True, slots=True)
class TimeGrowth:
    band: TimeBand
    fit: LogFit
    points: tuple[Point, ...]
    """The timings the fit used."""

    @property
    def sizes(self) -> tuple[int, ...]:
        return tuple(point.size for point in self.points)


@dataclass(frozen=True, slots=True)
class MemoryGrowth:
    band: MemoryBand
    fit: LogFit
    sizes: tuple[int, ...]


def classify_time(points: Sequence[Point]) -> TimeGrowth | None:
    """The band of usable timings; None (insufficient data) for fewer than three sizes."""
    if len(points) < MIN_FIT_SIZES:
        return None
    fit = log_log_fit(points)
    if _looks_exponential(points, fit):
        return TimeGrowth(TimeBand.X, fit, tuple(points))
    return TimeGrowth(time_band_of_slope(fit.slope), fit, tuple(points))


def classify_memory(points: Sequence[Point]) -> MemoryGrowth | None:
    if len(points) < MIN_FIT_SIZES:
        return None
    floored = [Point(point.size, max(point.value, CONSTANT_MEMORY_BYTES)) for point in points]
    fit = log_log_fit(floored)
    sizes = tuple(point.size for point in points)
    return MemoryGrowth(memory_band_of_slope(fit.slope), fit, sizes)


def _looks_exponential(points: Sequence[Point], fit: LogFit) -> bool:
    """A fit below the polynomial ceiling is exponential only when the curve accelerates past it:
    the local slope between the two largest sizes reaches the ceiling, the local slopes keep
    rising, and `log(time)` is more linear in n than in log n. Rising slopes alone also describe
    a fixed cost plus polynomial growth, whose slopes climb towards the polynomial's degree but
    never past it. A fit at or above the ceiling is X by its slope alone (`time_band_of_slope`):
    over the short ladders of exponential problems steep polynomial and exponential growth look
    alike, and their local slopes are often too even, or too noisy, to show acceleration."""
    local = [
        math.log(after.value / before.value) / math.log(after.size / before.size)
        for before, after in itertools.pairwise(points)
    ]
    if local[-1] < _POLYNOMIAL_CEILING:
        return False
    rising = all(later > earlier for earlier, later in itertools.pairwise(local))
    return rising and semi_log_fit(points).r2 > fit.r2


def _log(size: float) -> float:
    """Natural log, at least log 2, so the log classes stay positive at n = 1."""
    return math.log(max(size, 2.0))


_GROWTH: dict[ComplexityClass, Callable[[float], float]] = {
    ComplexityClass.CONSTANT: lambda n: 1.0,
    ComplexityClass.LOGARITHMIC: _log,
    ComplexityClass.SQUARE_ROOT: math.sqrt,
    ComplexityClass.LINEAR: lambda n: n,
    ComplexityClass.LINEARITHMIC: lambda n: n * _log(n),
    ComplexityClass.QUADRATIC: lambda n: n**2,
    ComplexityClass.QUADRATIC_LOGARITHMIC: lambda n: n**2 * _log(n),
    ComplexityClass.CUBIC: lambda n: n**3,
}
"""g(n) of the polynomial classes; the exponential ones have no single base to divide by."""


def class_drift(points: Sequence[Point], declared: ComplexityClass) -> float | None:
    """How far the declared class is from explaining `points`: the smallest spread (max over min)
    of `value / (a + g(n))` over fixed costs a >= 0, where g is the class's growth. a may dominate
    the smaller sizes but not the three largest, which must carry the growth: a series that never
    grows is not explained by a fixed cost. None for the exponential classes; needs three sizes.
    """
    growth = _GROWTH.get(declared)
    if growth is None:
        return None
    ordered = sorted(points, key=lambda point: point.size)
    terms = [(point.value, growth(point.size)) for point in ordered]
    largest_cost = terms[-MIN_FIT_SIZES][1]
    return min(_spread(terms, cost) for cost in _cost_candidates(terms, largest_cost))


def _spread(terms: Sequence[tuple[float, float]], cost: float) -> float:
    ratios = [value / (cost + growth) for value, growth in terms]
    return max(ratios) / min(ratios)


def _cost_candidates(terms: Sequence[tuple[float, float]], largest: float) -> list[float]:
    """Where the spread can be smallest: the ends of the range, and the costs at which two sizes
    swap places as the largest or smallest ratio (the spread is monotone in between)."""
    crossings = [
        (later_value * growth - value * later_growth) / (value - later_value)
        for (value, growth), (later_value, later_growth) in itertools.combinations(terms, 2)
        if value != later_value
    ]
    return [0.0, largest, *(cost for cost in crossings if 0.0 < cost < largest)]


def _least_squares(xs: Sequence[float], ys: Sequence[float]) -> LogFit:
    if len(set(xs)) < 2:
        raise ValueError("a fit needs at least two sizes")
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    spread_x = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / spread_x
    intercept = mean_y - slope * mean_x
    total = sum((y - mean_y) ** 2 for y in ys)
    residual = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys, strict=True))
    r2 = 1.0 if total == 0 else 1.0 - residual / total
    return LogFit(slope, intercept, r2)
