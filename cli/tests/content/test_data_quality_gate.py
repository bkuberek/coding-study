"""data-quality-gate promises that its hidden cases catch the classic mistakes of a data quality
gate: nulls failing checks that should skip them, integers and dates parsed too loosely or too
strictly, reports in the wrong order, duplicate keys counted or joined the wrong way, row-count
bounds rounded inward, drift bins closed on the wrong side or computed without the stated
epsilon, freshness read from the wrong event, and a gate that quarantines when it blocks, measures
the batch before quarantine, or moves its baseline on a blocked batch. These tests replay every
case against a model of the gate written from the statement, which must give every expected
output, and against that model with one mistake planted at a time, which some hidden case must
fail. The model parses with regular expressions and the calendar of the standard library, rounds
with decimal formatting and compares with exact fractions, where the reference counts characters,
checks days by hand and rounds in integer units. A mistake that crashes fails its case, as a
thrown exception does in the grader."""

import datetime
import json
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from decimal import Decimal
from fractions import Fraction
from typing import Any, ClassVar

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0336-data-quality-gate"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]
ROW_RULES = ("not-null", "type", "allowed", "range", "unique", "references")
BATCH_RULES = ("row-count", "drift", "freshness")
INT = re.compile(r"-?[0-9]{1,15}")
DATE = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})")


class Model:
    """The gate as the statement words it. Rules are dicts in a list; each mistake below overrides
    one rule of the statement."""

    def __init__(self, columns: list[str]) -> None:
        self.columns = list(columns)
        self.rules: list[dict[str, Any]] = []
        self.dimensions: dict[str, set[str]] = {}
        self.previous: list[list[str]] | None = None
        self.now = 0
        self.held: list[int] = []

    # --- parsing
    def is_null(self, value: str) -> bool:
        return value == ""

    def is_int(self, value: str) -> bool:
        return INT.fullmatch(value) is not None

    def is_date(self, value: str) -> bool:
        found = DATE.fullmatch(value)
        if found is None:
            return False
        try:
            datetime.date(*(int(part) for part in found.groups()))
        except ValueError:
            return False
        return True

    # --- row checks
    def value_fails(self, rule: dict[str, Any], value: str) -> bool:
        check, params = rule["check"], rule["params"]
        if check == "not-null":
            return self.is_null(value)
        if self.is_null(value):
            return False
        if check == "type":
            return not (self.is_int(value) if params[0] == "int" else self.is_date(value))
        if check == "allowed":
            return value not in params
        if check == "range":
            return self.is_int(value) and not self.in_range(int(value), params)
        return value not in self.dimensions[params[0]]

    def in_range(self, value: int, params: list[str]) -> bool:
        return int(params[0]) <= value <= int(params[1])

    def unique_key(self, row: list[str], rule: dict[str, Any]) -> tuple[str, ...] | None:
        key = tuple(row[self.columns.index(c)] for c in rule["columns"])
        return None if any(self.is_null(part) for part in key) else key

    def duplicates(self, rows: list[list[str]], rule: dict[str, Any]) -> list[int]:
        keys = [self.unique_key(row, rule) for row in rows]
        seen = Counter(key for key in keys if key is not None)
        return [at for at, key in enumerate(keys) if key is not None and seen[key] > 1]

    def failures_by_column(self, rule: dict[str, Any], rows: list[list[str]]) -> list[tuple]:
        if rule["check"] == "unique":
            return [("+".join(rule["columns"]), self.duplicates(rows, rule))]
        found = []
        for column in self.column_order(rule):
            at_column = self.columns.index(column)
            bad = [at for at, row in enumerate(rows) if self.value_fails(rule, row[at_column])]
            found.append((column, bad))
        return found

    def column_order(self, rule: dict[str, Any]) -> list[str]:
        return rule["columns"]

    # --- batch checks
    def bounds(self, before: int, tolerance: int) -> tuple[int, int]:
        low = Fraction(before * (100 - tolerance), 100)
        high = Fraction(before * (100 + tolerance), 100)
        return math.floor(low), math.ceil(high)

    def bin_of(self, value: int, edges: list[int]) -> int:
        return sum(1 for edge in edges if value >= edge)

    def shares(self, values: list[int], edges: list[int]) -> list[float]:
        counts = [0] * (len(edges) + 1)
        for value in values:
            counts[self.bin_of(value, edges)] += 1
        return [count / len(values) if count else 0.0001 for count in counts]

    def psi(self, actual: list[float], expected: list[float]) -> float:
        return sum((a - e) * math.log(a / e) for a, e in zip(actual, expected, strict=True))

    def drift_fails(self, rounded: str, threshold: str) -> bool:
        return Decimal(rounded) >= Decimal(threshold)

    def numbers(self, rows: list[list[str]], column: str) -> list[int]:
        at = self.columns.index(column)
        return [int(row[at]) for row in rows if self.is_int(row[at])]

    def newest(self, values: list[int]) -> int:
        return max(values)

    def stale(self, lag: int, limit: int) -> bool:
        return lag > limit

    def batch_observed(self, rule: dict[str, Any], rows: list[list[str]]) -> str | None:
        check, params = rule["check"], rule["params"]
        if check == "row-count":
            if self.previous is None:
                return None
            low, high = self.bounds(len(self.previous), int(params[0]))
            return None if low <= len(rows) <= high else str(len(rows))
        values = self.numbers(rows, rule["columns"][0])
        if check == "freshness":
            if not values:
                return "none"
            lag = self.now - self.newest(values)
            return str(lag) if self.stale(lag, int(params[0])) else None
        if self.previous is None:
            return None
        base = self.numbers(self.previous, rule["columns"][0])
        if not values or not base:
            return None
        edges = [int(edge) for edge in params[1:]]
        rounded = f"{self.psi(self.shares(values, edges), self.shares(base, edges)):.4f}"
        return rounded if self.drift_fails(rounded, params[0]) else None

    # --- reports
    def findings(self, rule: dict[str, Any], rows: list[list[str]]) -> list[list[str]]:
        if rule["check"] in BATCH_RULES:
            observed = self.batch_observed(rule, rows)
            column = rule["columns"][0] if rule["columns"] else ""
            return [] if observed is None else [[rule["id"], column, observed]]
        return [
            [rule["id"], column, str(len(bad))]
            for column, bad in self.failures_by_column(rule, rows)
            if self.reported(bad)
        ]

    def reported(self, bad: list[int]) -> bool:
        return len(bad) > 0

    def report_order(self) -> list[dict[str, Any]]:
        return self.rules

    def rule(self, rule_id: str) -> dict[str, Any] | None:
        return next((rule for rule in self.rules if rule["id"] == rule_id), None)

    def check_known(self, check: str) -> bool:
        return check in ROW_RULES + BATCH_RULES

    def default_action(self) -> str:
        return "block"

    def keep_after_quarantine(self, rows: list[list[str]], aside: set[int]) -> list[list[str]]:
        return [row for at, row in enumerate(rows) if at not in aside]

    def publish(self, kept: list[list[str]], rows: list[list[str]], aside: set[int]) -> None:
        self.previous = kept
        self.held = sorted(aside)

    def blocked(self, aside: set[int]) -> list[str]:
        self.held = []
        return ["block", "0", "0"]

    def may_quarantine(self, rule: dict[str, Any]) -> bool:
        return rule["check"] in ROW_RULES

    # --- level 1
    def add_rule(self, rule_id: str, check: str, columns: list[str], params: list[str]) -> bool:
        if self.rule(rule_id) or not self.check_known(check):
            return False
        if any(column not in self.columns for column in columns):
            return False
        if check == "references" and params[0] not in self.dimensions:
            return False
        self.rules.append(
            {
                "id": rule_id,
                "check": check,
                "columns": list(columns),
                "params": list(params),
                "action": self.default_action(),
            }
        )
        return True

    def validate(self, rows: list[list[str]]) -> list[list[str]]:
        return [entry for rule in self.report_order() for entry in self.findings(rule, rows)]

    def failing_rows(self, rows: list[list[str]], rule_id: str) -> list[int]:
        rule = self.rule(rule_id)
        if rule is None or rule["check"] in BATCH_RULES:
            return []
        return self.listed(bad for _, bad in self.failures_by_column(rule, rows))

    def listed(self, groups: Any) -> list[int]:
        return sorted({at for bad in groups for at in bad})

    # --- level 2
    def load_dimension(self, name: str, keys: list[str]) -> int:
        self.dimensions[name] = set(keys)
        return len(self.dimensions[name])

    def set_previous_batch(self, rows: list[list[str]]) -> int:
        self.previous = rows
        return len(rows)

    # --- level 3
    def set_time(self, now: int) -> None:
        self.now = now

    # --- level 4
    def set_action(self, rule_id: str, action: str) -> bool:
        rule = self.rule(rule_id)
        if rule is None or action not in ("warn", "quarantine", "block"):
            return False
        if action == "quarantine" and not self.may_quarantine(rule):
            return False
        rule["action"] = action
        return True

    def decide(self, rows: list[list[str]]) -> list[list[str]]:
        aside: set[int] = set()
        for rule in self.rules:
            if rule["check"] in ROW_RULES and rule["action"] == "quarantine":
                aside.update(self.failing_rows(rows, rule["id"]))
        kept = self.keep_after_quarantine(rows, aside)
        entries = []
        for rule in self.report_order():
            batch = rule["check"] in BATCH_RULES
            for entry in self.findings(rule, kept if batch else rows):
                entries.append([*entry, rule["action"]])
        if any(entry[3] == "block" for entry in entries):
            return [self.blocked(aside), *entries]
        self.publish(kept, rows, aside)
        return [["publish", str(len(kept)), str(len(aside))], *entries]

    def quarantined(self) -> list[int]:
        return self.held


# ------------------------------------------------------------------ level 1 mistakes
class NullFailsEveryCheck(Model):
    """Lets an empty value fail type, allowed and range too."""

    def value_fails(self, rule: dict[str, Any], value: str) -> bool:
        if self.is_null(value) and rule["check"] in ("type", "allowed", "range"):
            return True
        return super().value_fails(rule, value)


class BlankIsNull(Model):
    """Treats a value of spaces as null."""

    def is_null(self, value: str) -> bool:
        return value.strip() == ""


class IntegerTrimsSpaces(Model):
    """Reads an integer after trimming spaces."""

    def is_int(self, value: str) -> bool:
        return super().is_int(value.strip())


class IntegerOfAnyLength(Model):
    """Accepts integers of any number of digits."""

    def is_int(self, value: str) -> bool:
        return re.fullmatch(r"-?[0-9]+", value) is not None


class IntegerWithoutLeadingZeros(Model):
    """Refuses leading zeros."""

    def is_int(self, value: str) -> bool:
        return re.fullmatch(r"-?(0|[1-9][0-9]{0,14})", value) is not None


class LeapEveryFourYears(Model):
    """Makes every year divisible by 4 a leap year."""

    def is_date(self, value: str) -> bool:
        found = DATE.fullmatch(value)
        if found and found.group(2) == "02" and found.group(3) == "29":
            year = int(found.group(1))
            return year > 0 and year % 4 == 0
        return super().is_date(value)


class EveryMonthHasThirtyOneDays(Model):
    """Checks only that the day is from 1 to 31."""

    def is_date(self, value: str) -> bool:
        found = DATE.fullmatch(value)
        if found is None:
            return False
        year, month, day = (int(part) for part in found.groups())
        return year >= 1 and 1 <= month <= 12 and 1 <= day <= 31


class ExclusiveRange(Model):
    """Excludes the bounds of a range."""

    def in_range(self, value: int, params: list[str]) -> bool:
        return int(params[0]) < value < int(params[1])


class RangeFailsNonIntegers(Model):
    """Counts a value that is not an integer as out of range."""

    def value_fails(self, rule: dict[str, Any], value: str) -> bool:
        if rule["check"] == "range" and not self.is_null(value) and not self.is_int(value):
            return True
        return super().value_fails(rule, value)


class AllowedIgnoresCase(Model):
    """Compares allowed values without regard to case."""

    def value_fails(self, rule: dict[str, Any], value: str) -> bool:
        if rule["check"] == "allowed" and not self.is_null(value):
            return value.lower() not in [param.lower() for param in rule["params"]]
        return super().value_fails(rule, value)


class ReportByRuleId(Model):
    """Sorts the report by rule id."""

    def report_order(self) -> list[dict[str, Any]]:
        return sorted(self.rules, key=lambda rule: rule["id"])


class ColumnsInSchemaOrder(Model):
    """Lists a rule's columns in the order of the batch."""

    def column_order(self, rule: dict[str, Any]) -> list[str]:
        return [column for column in self.columns if column in rule["columns"]]


class ReportsPassingColumns(Model):
    """Lists columns with no failure, with a count of 0."""

    def reported(self, bad: list[int]) -> bool:
        return True


class RowListedOncePerColumn(Model):
    """Lists a row once for every column where it fails."""

    def listed(self, groups: Any) -> list[int]:
        return sorted(at for bad in groups for at in bad)


class CheckNamesIgnoreCase(Model):
    """Accepts check names in any case."""

    def check_known(self, check: str) -> bool:
        return check.lower() in ROW_RULES + BATCH_RULES

    def add_rule(self, rule_id: str, check: str, columns: list[str], params: list[str]) -> bool:
        return super().add_rule(rule_id, check.lower(), columns, params)


class SecondRuleWithAnIdReplacesIt(Model):
    """Replaces a rule when its id is used again."""

    def add_rule(self, rule_id: str, check: str, columns: list[str], params: list[str]) -> bool:
        self.rules = [rule for rule in self.rules if rule["id"] != rule_id]
        return super().add_rule(rule_id, check, columns, params)


# ------------------------------------------------------------------ level 2 mistakes
class UniqueCountsOnlyExtraCopies(Model):
    """Counts the copies after the first one only."""

    def duplicates(self, rows: list[list[str]], rule: dict[str, Any]) -> list[int]:
        seen: set[tuple[str, ...]] = set()
        extra = []
        for at, row in enumerate(rows):
            key = self.unique_key(row, rule)
            if key is not None and key in seen:
                extra.append(at)
            if key is not None:
                seen.add(key)
        return extra


class UniqueJoinsTheKey(Model):
    """Joins the key columns into one text with no separator."""

    def unique_key(self, row: list[str], rule: dict[str, Any]) -> tuple[str, ...] | None:
        key = super().unique_key(row, rule)
        return None if key is None else ("".join(key),)


class UniqueJoinsWithABar(Model):
    """Joins the key columns with a bar."""

    def unique_key(self, row: list[str], rule: dict[str, Any]) -> tuple[str, ...] | None:
        key = super().unique_key(row, rule)
        return None if key is None else ("|".join(key),)


class UniqueComparesNullKeys(Model):
    """Checks keys that hold a null like any other."""

    def unique_key(self, row: list[str], rule: dict[str, Any]) -> tuple[str, ...] | None:
        return tuple(row[self.columns.index(c)] for c in rule["columns"])


class ReferenceFailsNull(Model):
    """Fails an empty reference."""

    def value_fails(self, rule: dict[str, Any], value: str) -> bool:
        if rule["check"] == "references" and self.is_null(value):
            return True
        return super().value_fails(rule, value)


class ReferenceKeysCopiedWhenAdded(Model):
    """Keeps the dimension keys as they were when the rule was added."""

    def add_rule(self, rule_id: str, check: str, columns: list[str], params: list[str]) -> bool:
        added = super().add_rule(rule_id, check, columns, params)
        if added and check == "references":
            frozen = f"{params[0]}@{rule_id}"
            self.dimensions[frozen] = set(self.dimensions[params[0]])
            self.rules[-1]["params"] = [frozen]
        return added


class ReferenceToAnyDimension(Model):
    """Accepts a reference to a dimension that was never loaded."""

    def add_rule(self, rule_id: str, check: str, columns: list[str], params: list[str]) -> bool:
        if check == "references":
            self.dimensions.setdefault(params[0], set())
        return super().add_rule(rule_id, check, columns, params)


class RowCountWithoutRounding(Model):
    """Compares the count with the exact bounds."""

    def bounds(self, before: int, tolerance: int) -> tuple[int, int]:
        low = Fraction(before * (100 - tolerance), 100)
        high = Fraction(before * (100 + tolerance), 100)
        return math.ceil(low), math.floor(high)


class RowCountFailsTheFirstBatch(Model):
    """Fails the count when there is no previous batch."""

    def batch_observed(self, rule: dict[str, Any], rows: list[list[str]]) -> str | None:
        if rule["check"] == "row-count" and self.previous is None:
            return str(len(rows))
        return super().batch_observed(rule, rows)


class EmptyPreviousIsNoPrevious(Model):
    """Treats an empty previous batch as no previous batch."""

    def set_previous_batch(self, rows: list[list[str]]) -> int:
        self.previous = rows or None
        return len(rows)


# ------------------------------------------------------------------ level 3 mistakes
class EdgeBelongsBelow(Model):
    """Puts a value equal to an edge into the bin below it."""

    def bin_of(self, value: int, edges: list[int]) -> int:
        return sum(1 for edge in edges if value > edge)


class EmptyBinsSkipped(Model):
    """Leaves out a bin that is empty in either batch."""

    def shares(self, values: list[int], edges: list[int]) -> list[float]:
        counts = [0] * (len(edges) + 1)
        for value in values:
            counts[self.bin_of(value, edges)] += 1
        return [count / len(values) for count in counts]

    def psi(self, actual: list[float], expected: list[float]) -> float:
        pairs = zip(actual, expected, strict=True)
        return sum((a - e) * math.log(a / e) for a, e in pairs if a > 0 and e > 0)


class OneSidedDivergence(Model):
    """Computes the divergence one way only, sum of a * ln(a / e)."""

    def psi(self, actual: list[float], expected: list[float]) -> float:
        return sum(a * math.log(a / e) for a, e in zip(actual, expected, strict=True))


class DriftCountsEveryRow(Model):
    """Divides by the number of rows, not the number of integers."""

    def batch_observed(self, rule: dict[str, Any], rows: list[list[str]]) -> str | None:
        if rule["check"] != "drift" or self.previous is None:
            return super().batch_observed(rule, rows)
        values = self.numbers(rows, rule["columns"][0])
        base = self.numbers(self.previous, rule["columns"][0])
        if not values or not base:
            return None
        edges = [int(edge) for edge in rule["params"][1:]]

        def shares(sample: list[int], total: int) -> list[float]:
            counts = [0] * (len(edges) + 1)
            for value in sample:
                counts[self.bin_of(value, edges)] += 1
            return [count / total if count else 0.0001 for count in counts]

        value = self.psi(shares(values, len(rows)), shares(base, len(self.previous)))
        rounded = f"{value:.4f}"
        return rounded if self.drift_fails(rounded, rule["params"][0]) else None


class DriftThresholdIsStrict(Model):
    """Fails drift only above the threshold."""

    def drift_fails(self, rounded: str, threshold: str) -> bool:
        return Decimal(rounded) > Decimal(threshold)


class FreshnessFromTheOldestEvent(Model):
    """Measures the lag from the oldest event."""

    def newest(self, values: list[int]) -> int:
        return min(values)


class FreshnessFromTheLastRow(Model):
    """Measures the lag from the last row's event."""

    def newest(self, values: list[int]) -> int:
        return values[-1]


class FreshnessLimitIsExclusive(Model):
    """Fails a lag equal to the limit."""

    def stale(self, lag: int, limit: int) -> bool:
        return lag >= limit


class FreshnessPassesWithoutEvents(Model):
    """Passes a batch with no event time."""

    def batch_observed(self, rule: dict[str, Any], rows: list[list[str]]) -> str | None:
        observed = super().batch_observed(rule, rows)
        return None if observed == "none" else observed


class FutureEventsAreLate(Model):
    """Measures the lag as a distance, so events after now count as late."""

    def stale(self, lag: int, limit: int) -> bool:
        return abs(lag) > limit


class DriftWithTwoDecimals(Model):
    """Writes the drift with two decimals."""

    def batch_observed(self, rule: dict[str, Any], rows: list[list[str]]) -> str | None:
        observed = super().batch_observed(rule, rows)
        if rule["check"] == "drift" and observed is not None:
            return f"{Decimal(observed):.2f}"
        return observed


# ------------------------------------------------------------------ level 4 mistakes
class RulesWarnByDefault(Model):
    """Starts every rule as a warning."""

    def default_action(self) -> str:
        return "warn"


class BatchRulesMayQuarantine(Model):
    """Accepts quarantine for row-count, drift and freshness."""

    def may_quarantine(self, rule: dict[str, Any]) -> bool:
        return True


class BlockStillQuarantines(Model):
    """Reports and keeps the rows set aside even when the batch is blocked."""

    def blocked(self, aside: set[int]) -> list[str]:
        self.held = sorted(aside)
        return ["block", "0", str(len(aside))]


class BlockedBatchBecomesPrevious(Model):
    """Moves the baseline to every batch, published or not."""

    def blocked(self, aside: set[int]) -> list[str]:
        self.previous = self.pending
        return super().blocked(aside)

    def decide(self, rows: list[list[str]]) -> list[list[str]]:
        self.pending = rows
        return super().decide(rows)


class BatchRulesSeeEveryRow(Model):
    """Runs row-count, drift and freshness on the batch before quarantine."""

    def decide(self, rows: list[list[str]]) -> list[list[str]]:
        self.everything = rows
        return super().decide(rows)

    def findings(self, rule: dict[str, Any], rows: list[list[str]]) -> list[list[str]]:
        if rule["check"] in BATCH_RULES and hasattr(self, "everything"):
            return super().findings(rule, self.everything)
        return super().findings(rule, rows)


class BaselineKeepsQuarantinedRows(Model):
    """Makes the whole batch the baseline, rows set aside included."""

    def publish(self, kept: list[list[str]], rows: list[list[str]], aside: set[int]) -> None:
        super().publish(kept, rows, aside)
        self.previous = rows


class RowRulesReportedFirst(Model):
    """Lists the findings of row rules before those of batch rules."""

    def decide(self, rows: list[list[str]]) -> list[list[str]]:
        head, *entries = super().decide(rows)
        rank = {rule["id"]: rule["check"] in BATCH_RULES for rule in self.rules}
        return [head, *sorted(entries, key=lambda entry: rank[entry[0]])]


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type(*case["args"][0])
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, ZeroDivisionError, AttributeError):
        return False


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


class DriftProbe(Model):
    """Records every drift value it computes, before rounding."""

    seen: ClassVar[list[float]] = []

    def psi(self, actual: list[float], expected: list[float]) -> float:
        value = super().psi(actual, expected)
        DriftProbe.seen.append(value)
        return value


def test_no_drift_lands_near_a_rounding_tie():
    """Every language rounds the same double; keep each one far from a half unit of 0.0001, so a
    last-bit difference in a logarithm can never change the text or the decision."""
    DriftProbe.seen = []
    for case in SCRIPTED_CASES:
        outputs(DriftProbe, case)
    assert DriftProbe.seen
    for value in DriftProbe.seen:
        fraction = value * 10000 - math.floor(value * 10000)
        assert abs(fraction - 0.5) > 1e-6, value
