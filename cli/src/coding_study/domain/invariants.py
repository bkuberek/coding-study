"""Judging one stress run's record against its invariants.

Spec: docs/specs/problem-format.md#invariants. Values compare as canonical JSON with the
comparators' type-strict equality (`true` never equals `1`; `1` equals `1.0`); `min` and `max`
are inclusive. Each failing invariant gives one reason that names the evidence: the missing,
extra or repeated values, or the counters that broke a bound.
"""

from collections import Counter as Tally
from collections.abc import Callable, Hashable, Mapping, Sequence
from dataclasses import dataclass

from coding_study.domain.cases import JsonValue
from coding_study.domain.comparators import canonical_key
from coding_study.domain.runs import SectionCounters
from coding_study.domain.stress import (
    Bounds,
    CheckerInvariant,
    Count,
    Distinct,
    EqualMultisets,
    Invariant,
    SectionBounds,
    Selector,
    SourceOrder,
    Sum,
)
from coding_study.domain.stress_record import StressRecord
from coding_study.domain.value_text import value_text

type StressChecker = Callable[[str, dict[str, JsonValue], dict[str, JsonValue]], str | None]
"""`check(name, scenario, run)` from a problem's stress_checker.py: None when the run satisfies
the named invariant, otherwise a one-line reason."""

SHOWN_VALUES = 3
"""Values named in one reason; the rest are counted."""
NO_SECTION = SectionCounters(entries=0, violations=0, max_occupancy=0)


@dataclass(frozen=True, slots=True)
class InvariantContext:
    scenario: Mapping[str, JsonValue]
    """The case's `stress` object as written."""
    checker: StressChecker | None = None
    """None when the problem has no stress_checker.py."""


def invariant_failures(
    invariants: Sequence[Invariant], record: StressRecord, context: InvariantContext
) -> tuple[str, ...]:
    """One reason per failing invariant, in declaration order."""
    reasons = (_failure(invariant, record, context) for invariant in invariants)
    return tuple(reason for reason in reasons if reason is not None)


def _failure(invariant: Invariant, record: StressRecord, context: InvariantContext) -> str | None:
    match invariant:
        case EqualMultisets(left=left, right=right):
            return _equal_multisets(left, right, record)
        case Distinct(values=values):
            return _distinct(values, record)
        case Bounds(values=values, minimum=minimum, maximum=maximum):
            return _bounds(values, record, (minimum, maximum))
        case Count():
            return _count(invariant, record)
        case Sum(values=values, minimum=minimum, maximum=maximum):
            return _sum(values, record, (minimum, maximum))
        case SourceOrder(values=values, stride=stride):
            return _source_order(values, stride, record)
        case SectionBounds():
            return _section(invariant, record.sections.get(invariant.name, NO_SECTION))
        case CheckerInvariant(name=name):
            return _checker(name, record, context)


def _equal_multisets(left: Selector, right: Selector, record: StressRecord) -> str | None:
    left_values, right_values = record.values(left), record.values(right)
    left_counts, right_counts = _counts(left_values), _counts(right_values)
    missing = left_counts - right_counts
    extra = right_counts - left_counts
    if not missing and not extra:
        return None
    examples = _Examples(left_values + right_values)
    return (
        f"equal_multisets {left.label()} vs {right.label()}: "
        f"{missing.total()} missing{examples.listed(missing)}, "
        f"{extra.total()} extra{examples.listed(extra)}"
    )


def _distinct(selector: Selector, record: StressRecord) -> str | None:
    values = record.values(selector)
    repeated = Tally({key: count for key, count in _counts(values).items() if count > 1})
    if not repeated:
        return None
    examples = _Examples(values)
    shown = ", ".join(
        f"{examples.text(key)} ({count} times)" for key, count in list(repeated.items())[:3]
    )
    more = len(repeated) - SHOWN_VALUES
    rest = f" and {more} more" if more > 0 else ""
    return f"distinct {selector.label()}: {shown}{rest}"


type _Range = tuple[float | None, float | None]


def _bounds(selector: Selector, record: StressRecord, bounds: _Range) -> str | None:
    values = record.values(selector)
    outside = [value for value in values if not _within(value, bounds)]
    if not outside:
        return None
    shown = ", ".join(value_text(value) for value in outside[:SHOWN_VALUES])
    more = len(outside) - SHOWN_VALUES
    rest = f" and {more} more" if more > 0 else ""
    return f"bounds {selector.label()}: {shown}{rest} outside {_range_text(bounds)}"


def _count(invariant: Count, record: StressRecord) -> str | None:
    count = len(record.values(invariant.values))
    label = invariant.values.label()
    if invariant.equals is not None and count != invariant.equals:
        return f"count {label}: {count}, expected {invariant.equals}"
    bounds: _Range = (invariant.minimum, invariant.maximum)
    if not _within(count, bounds):
        return f"count {label}: {count} outside {_range_text(bounds)}"
    return None


def _sum(selector: Selector, record: StressRecord, bounds: _Range) -> str | None:
    numbers = _numbers(record.values(selector))
    if numbers is None:
        return f"sum {selector.label()}: not every value is a number"
    total = sum(numbers)
    if _within(total, bounds):
        return None
    return f"sum {selector.label()}: {value_text(total)} outside {_range_text(bounds)}"


def _source_order(selector: Selector, stride: int, record: StressRecord) -> str | None:
    for label, sequence in record.sequences(selector):
        latest: dict[int, int] = {}
        for value in sequence:
            if not isinstance(value, int) or isinstance(value, bool):
                continue
            source = value // stride
            earlier = latest.get(source)
            if earlier is not None and value <= earlier:
                return f"source_order {selector.label()}: {label} got {value} after {earlier}"
            latest[source] = value
    return None


def _section(invariant: SectionBounds, counters: SectionCounters) -> str | None:
    name = f"section {invariant.name}"
    if counters.violations > invariant.max_violations:
        noun = "violation" if counters.violations == 1 else "violations"
        return (
            f"{name}: {counters.violations} {noun} in {counters.entries} entries "
            f"(at most {invariant.max_violations})"
        )
    occupancy = counters.max_occupancy
    if invariant.max_occupancy is not None and occupancy > invariant.max_occupancy:
        return f"{name}: max occupancy {occupancy}, at most {invariant.max_occupancy}"
    if invariant.min_occupancy is not None and occupancy < invariant.min_occupancy:
        return f"{name}: max occupancy {occupancy}, at least {invariant.min_occupancy} expected"
    return None


def _checker(name: str, record: StressRecord, context: InvariantContext) -> str | None:
    if context.checker is None:
        return f"checker {name}: the problem has no stress_checker.py"
    try:
        reason = context.checker(name, dict(context.scenario), record.document())
    except Exception as error:  # content code: any failure fails the run
        return f"checker {name} raised {type(error).__name__}: {error}"
    return None if reason is None else f"checker {name}: {reason}"


def _counts(values: Sequence[JsonValue]) -> Tally[Hashable]:
    return Tally(map(canonical_key, values))


class _Examples:
    """Shows canonical keys as the values they came from."""

    def __init__(self, values: Sequence[JsonValue]) -> None:
        self._values = {canonical_key(value): value for value in values}

    def text(self, key: Hashable) -> str:
        return value_text(self._values[key])

    def listed(self, counts: Tally[Hashable]) -> str:
        if not counts:
            return ""
        keys = list(counts)
        shown = ", ".join(self.text(key) for key in keys[:SHOWN_VALUES])
        more = len(keys) - SHOWN_VALUES
        return f" ({shown}{f', and {more} more' if more > 0 else ''})"


def _numbers(values: Sequence[JsonValue]) -> list[int | float] | None:
    """The values as numbers; None when any is not a number (booleans are not)."""
    numbers = [
        value for value in values if isinstance(value, int | float) and not isinstance(value, bool)
    ]
    return numbers if len(numbers) == len(values) else None


def _within(value: JsonValue, bounds: _Range) -> bool:
    numbers = _numbers([value])
    if not numbers:
        return False
    number = numbers[0]
    minimum, maximum = bounds
    return (minimum is None or number >= minimum) and (maximum is None or number <= maximum)


def _range_text(bounds: _Range) -> str:
    minimum, maximum = bounds
    low = "-inf" if minimum is None else value_text(minimum)
    high = "inf" if maximum is None else value_text(maximum)
    return f"[{low}, {high}]"
