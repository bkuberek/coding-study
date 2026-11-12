"""slo-burn-rate promises that its hidden cases catch the classic mistakes of turning counters into
service level alerts: a counter reset read as a drop or ignored, a rate divided by the wrong
duration, a histogram quantile taken from the wrong bucket or not interpolated, an error budget
measured against the objective instead of what it leaves, a time to exhaustion rounded the wrong
way, and an alert that needs only one of its two windows or fires at the threshold. These tests
replay every case against a model of the monitor written from the statement with exact
fractions, which must give every expected output, and against that model with one mistake
planted at a time, which some hidden case must fail. A mistake that crashes fails its case, as a
thrown exception does in the grader."""

import itertools
import json
import math
import re
from collections.abc import Mapping, Sequence
from fractions import Fraction
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0374-slo-burn-rate"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]


def read(text: str) -> Fraction:
    return Fraction(text)


class Model:
    """The monitor as the statement words it, with Python fractions for every ratio. Each mistake
    below overrides one rule."""

    def __init__(self) -> None:
        self.samples: dict[str, list[tuple[int, int]]] = {}
        self.bounds: dict[str, list[int]] = {}
        self.slos: dict[str, tuple[str, str, Fraction, int]] = {}
        self.alerts: dict[str, list[tuple[str, int, int, Fraction]]] = {}

    def show(self, value: Fraction) -> str:
        return str(value)

    # --- level 1
    def accepts(self, series: str, timestamp: int) -> bool:
        have = self.samples.get(series, [])
        return not have or timestamp > have[-1][0]

    def scrape(self, series: str, timestamp: int, value: int) -> str:
        if not self.accepts(series, timestamp):
            return "out-of-order"
        self.samples.setdefault(series, []).append((timestamp, value))
        return "ok"

    def scrape_series(self, series: str, start: int, step: int, values: list[int]) -> int:
        return [self.scrape(series, start + i * step, v) for i, v in enumerate(values)].count("ok")

    def inside(self, series: str, start: int, end: int) -> list[tuple[int, int]]:
        return [(t, v) for t, v in self.samples.get(series, []) if start <= t <= end]

    def step(self, before: int, after: int) -> int:
        return after - before if after >= before else after

    def too_few(self) -> int:
        return -1

    def increase(self, series: str, start: int, end: int) -> int:
        got = self.inside(series, start, end)
        if len(got) < 2:
            return self.too_few()
        return sum(self.step(a, b) for (_, a), (_, b) in itertools.pairwise(got))

    def duration(self, got: list[tuple[int, int]], start: int, end: int) -> int:
        return got[-1][0] - got[0][0]

    def rate(self, series: str, start: int, end: int) -> str:
        got = self.inside(series, start, end)
        if len(got) < 2:
            return ""
        return self.show(
            Fraction(self.increase(series, start, end), self.duration(got, start, end))
        )

    def is_reset(self, before: int, after: int) -> bool:
        return after < before

    def resets(self, series: str, start: int, end: int) -> int:
        got = self.inside(series, start, end)
        return sum(self.is_reset(a, b) for (_, a), (_, b) in itertools.pairwise(got))

    # --- level 2
    def scrape_histogram(
        self, name: str, timestamp: int, bounds: list[int], counts: list[int]
    ) -> str:
        if not self.accepts(f"{name}:le=inf", timestamp):
            return "out-of-order"
        self.bounds[name] = bounds
        for label, count in zip([*bounds, "inf"], counts, strict=True):
            self.scrape(f"{name}:le={label}", timestamp, count)
        return "ok"

    def window_counts(self, name: str, start: int, end: int) -> list[int] | None:
        if name not in self.bounds:
            return None
        found = [self.increase(f"{name}:le={b}", start, end) for b in [*self.bounds[name], "inf"]]
        return found if found[-1] > 0 else None

    def within(self, name: str, threshold: int, counts: list[int]) -> Fraction | None:
        if threshold not in self.bounds[name]:
            return None
        return Fraction(counts[self.bounds[name].index(threshold)], counts[-1])

    def fraction_within(self, name: str, threshold: int, start: int, end: int) -> str:
        counts = self.window_counts(name, start, end)
        if counts is None:
            return ""
        found = self.within(name, threshold, counts)
        return "" if found is None else self.show(found)

    def reaches(self, count: int, rank: Fraction) -> bool:
        return count >= rank

    def rank(self, q: Fraction, total: int) -> Fraction:
        return q * total

    def lowest_floor(self, bounds: list[int]) -> int:
        return 0

    def top_bucket(self, bounds: list[int]) -> str:
        return str(bounds[-1])

    def interpolate(self, low: int, high: int, rank: Fraction, before: int, count: int) -> Fraction:
        return low + (high - low) * (rank - before) / (count - before)

    def quantile(self, name: str, q: str, start: int, end: int) -> str:
        counts = self.window_counts(name, start, end)
        if counts is None:
            return ""
        bounds = self.bounds[name]
        rank = self.rank(read(q), counts[-1])
        index = next(i for i, c in enumerate(counts) if self.reaches(c, rank))
        if index == len(bounds):
            return self.top_bucket(bounds)
        low = bounds[index - 1] if index else self.lowest_floor(bounds)
        before = counts[index - 1] if index else 0
        return self.show(self.interpolate(low, bounds[index], rank, before, counts[index]))

    # --- level 3
    def objective_ok(self, objective: Fraction) -> bool:
        return 0 < objective < 1

    def define_slo(self, name: str, good: str, total: str, objective: str, window: int) -> str:
        if name in self.slos:
            return "duplicate"
        if not self.objective_ok(read(objective)):
            return "bad-objective"
        self.slos[name] = (good, total, read(objective), window)
        self.alerts[name] = []
        return "ok"

    def window_start(self, at: int, span: int) -> int:
        return at - span

    def ratio(self, name: str, at: int, span: int) -> Fraction | None:
        """The share of good requests over [at - span, at]."""
        good, total, _, _ = self.slos[name]
        t = self.increase(total, self.window_start(at, span), at)
        g = self.increase(good, self.window_start(at, span), at)
        if t <= 0 or g < 0:
            return None
        return Fraction(g, t)

    def budget(self, name: str) -> Fraction:
        return 1 - self.slos[name][2]

    def sli(self, name: str, at: int) -> str:
        if name not in self.slos:
            return ""
        found = self.ratio(name, at, self.slos[name][3])
        return "" if found is None else self.show(found)

    def left(self, name: str, at: int) -> Fraction | None:
        found = self.ratio(name, at, self.slos[name][3])
        return None if found is None else 1 - (1 - found) / self.budget(name)

    def budget_remaining(self, name: str, at: int) -> str:
        if name not in self.slos:
            return ""
        found = self.left(name, at)
        return "" if found is None else self.show(found)

    def burn(self, name: str, at: int, lookback: int) -> Fraction | None:
        found = self.ratio(name, at, lookback)
        return None if found is None else (1 - found) / self.budget(name)

    def burn_rate(self, name: str, at: int, lookback: int) -> str:
        if name not in self.slos:
            return ""
        found = self.burn(name, at, lookback)
        return "" if found is None else self.show(found)

    def round_time(self, value: Fraction) -> int:
        return math.floor(value)

    def spent(self, remaining: Fraction) -> int:
        return 0

    def time_to_exhaustion(self, name: str, at: int, lookback: int) -> int:
        if name not in self.slos:
            return -1
        remaining = self.left(name, at)
        if remaining is None:
            return -1
        if remaining <= 0:
            return self.spent(remaining)
        speed = self.burn(name, at, lookback)
        if not speed:
            return -1
        return self.round_time(remaining * self.slos[name][3] / speed)

    # --- level 4
    def windows_ok(self, long_window: int, short_window: int) -> bool:
        return long_window > 0 and 0 <= short_window < long_window

    def add_alert(
        self, slo: str, severity: str, long_window: int, short_window: int, threshold: str
    ) -> str:
        if slo not in self.slos:
            return "unknown-slo"
        if any(a[0] == severity for a in self.alerts[slo]):
            return "duplicate"
        if not self.windows_ok(long_window, short_window):
            return "bad-windows"
        self.alerts[slo].append((severity, long_window, short_window, read(threshold)))
        return "ok"

    def above(self, burn: Fraction | None, threshold: Fraction) -> bool:
        return burn is not None and burn > threshold

    def combine(self, long_hot: bool, short_hot: bool | None) -> bool:
        return long_hot and (short_hot is None or short_hot)

    def fires(self, slo: str, alert: tuple[str, int, int, Fraction], at: int) -> bool:
        _, long_window, short_window, threshold = alert
        long_hot = self.above(self.burn(slo, at, long_window), threshold)
        short_hot = (
            None if short_window == 0 else self.above(self.burn(slo, at, short_window), threshold)
        )
        return self.combine(long_hot, short_hot)

    def firing(self, slo: str, at: int) -> list[str]:
        return [a[0] for a in self.alerts.get(slo, []) if self.fires(slo, a, at)]

    def instants(self, start: int, end: int, step: int) -> range:
        return range(start, end + 1, step)

    def order_events(self, events: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
        return events

    def timeline(self, slo: str, start: int, end: int, step: int) -> list[str]:
        alerts = self.alerts.get(slo, [])
        was = {a[0]: False for a in alerts}
        events = []
        for at in self.instants(start, end, step):
            for position, alert in enumerate(alerts):
                now = self.fires(slo, alert, at)
                if now != was[alert[0]]:
                    events.append((at, position, f"{at} {alert[0]} {'start' if now else 'stop'}"))
                    was[alert[0]] = now
        return [line for _, _, line in self.order_events(events)]


# ------------------------------------------------------------------ level 1 mistakes
class ResetsIgnored(Model):
    """Takes the last sample minus the first, as if counters never restarted."""

    def increase(self, series: str, start: int, end: int) -> int:
        got = self.inside(series, start, end)
        return got[-1][1] - got[0][1] if len(got) >= 2 else -1


class ResetAddsNothing(Model):
    """Skips the step across a restart instead of counting the new value."""

    def step(self, before: int, after: int) -> int:
        return max(after - before, 0)


class ResetCountsNegative(Model):
    """Adds the drop of a restart as a negative step."""

    def step(self, before: int, after: int) -> int:
        return after - before


class RateOverTheWholeWindow(Model):
    """Divides by the length of the window asked for, not by the time the samples span."""

    def duration(self, got: list[tuple[int, int]], start: int, end: int) -> int:
        return end - start


class WindowEndExcluded(Model):
    """Leaves out a sample taken exactly at the end of the window."""

    def inside(self, series: str, start: int, end: int) -> list[tuple[int, int]]:
        return [(t, v) for t, v in self.samples.get(series, []) if start <= t < end]


class WindowStartExcluded(Model):
    """Leaves out a sample taken exactly at the start of the window."""

    def inside(self, series: str, start: int, end: int) -> list[tuple[int, int]]:
        return [(t, v) for t, v in self.samples.get(series, []) if start < t <= end]


class BaselineBeforeTheWindow(Model):
    """Starts from the last sample before the window, as a delta between two readings would."""

    def inside(self, series: str, start: int, end: int) -> list[tuple[int, int]]:
        every = self.samples.get(series, [])
        earlier = [s for s in every if s[0] < start]
        return earlier[-1:] + super().inside(series, start, end)


class EqualTimestampReplaces(Model):
    """Accepts a sample with the time of the last one and keeps the newer value."""

    def scrape(self, series: str, timestamp: int, value: int) -> str:
        have = self.samples.get(series, [])
        if have and timestamp == have[-1][0]:
            have[-1] = (timestamp, value)
            return "ok"
        return super().scrape(series, timestamp, value)


class OlderSamplesInserted(Model):
    """Accepts a late sample and files it in time order."""

    def scrape(self, series: str, timestamp: int, value: int) -> str:
        have = self.samples.setdefault(series, [])
        if any(t == timestamp for t, _ in have):
            return "out-of-order"
        have.append((timestamp, value))
        have.sort()
        return "ok"


class NoSamplesMeansZero(Model):
    """Reports an increase of 0 when the window holds fewer than two samples."""

    def too_few(self) -> int:
        return 0


class FractionsNotReduced(Model):
    """Writes a ratio without reducing it to lowest terms."""

    def rate(self, series: str, start: int, end: int) -> str:
        got = self.inside(series, start, end)
        if len(got) < 2:
            return ""
        return f"{self.increase(series, start, end)}/{got[-1][0] - got[0][0]}"


class WholeNumbersWithDenominator(Model):
    """Writes 5 as 5/1."""

    def show(self, value: Fraction) -> str:
        return f"{value.numerator}/{value.denominator}"


class EqualValuesAreAReset(Model):
    """Counts a counter that did not move as restarted."""

    def is_reset(self, before: int, after: int) -> bool:
        return after <= before


class ScrapeSeriesCountsEverything(Model):
    """Returns how many values were given, not how many were stored."""

    def scrape_series(self, series: str, start: int, step: int, values: list[int]) -> int:
        super().scrape_series(series, start, step, values)
        return len(values)


# ------------------------------------------------------------------ level 2 mistakes
class BucketStrictlyAboveTheRank(Model):
    """Picks the first bucket whose count is above the rank, not the first that reaches it."""

    def reaches(self, count: int, rank: Fraction) -> bool:
        return count > rank


class FirstBucketStartsAtItsBound(Model):
    """Gives the lowest bucket no width, so every quantile in it is its upper bound."""

    def lowest_floor(self, bounds: list[int]) -> int:
        return bounds[0]


class NoInterpolation(Model):
    """Answers with the upper bound of the bucket that holds the quantile."""

    def interpolate(self, low: int, high: int, rank: Fraction, before: int, count: int) -> Fraction:
        return Fraction(high)


class InterpolatesFromItsOwnCount(Model):
    """Reads the cumulative count of the bucket as the number of requests inside it."""

    def interpolate(self, low: int, high: int, rank: Fraction, before: int, count: int) -> Fraction:
        return low + (high - low) * (rank - before) / count


class TopBucketGivesNothing(Model):
    """Has no answer for a quantile in the bucket above every bound."""

    def top_bucket(self, bounds: list[int]) -> str:
        return ""


class RankRoundedDown(Model):
    """Rounds the rank down to a whole request."""

    def rank(self, q: Fraction, total: int) -> Fraction:
        return Fraction(math.floor(q * total))


class ThresholdBetweenBoundsInterpolated(Model):
    """Interpolates the share of requests below a threshold that is not a bound."""

    def within(self, name: str, threshold: int, counts: list[int]) -> Fraction | None:
        bounds = self.bounds[name]
        if threshold in bounds:
            return super().within(name, threshold, counts)
        for i, bound in enumerate(bounds):
            if threshold < bound:
                low = bounds[i - 1] if i else 0
                before = counts[i - 1] if i else 0
                inside = before + Fraction(counts[i] - before) * (threshold - low) / (bound - low)
                return inside / counts[-1]
        return Fraction(counts[-2], counts[-1])


class HistogramFromEndpoints(Model):
    """Subtracts the first histogram of the window from the last, ignoring restarts in between."""

    def window_counts(self, name: str, start: int, end: int) -> list[int] | None:
        if name not in self.bounds:
            return None
        found = []
        for b in [*self.bounds[name], "inf"]:
            got = self.inside(f"{name}:le={b}", start, end)
            found.append(got[-1][1] - got[0][1] if len(got) >= 2 else -1)
        return found if found[-1] > 0 else None


# ------------------------------------------------------------------ level 3 mistakes
class BudgetIsTheObjective(Model):
    """Measures errors against the objective instead of the budget it leaves."""

    def budget(self, name: str) -> Fraction:
        return self.slos[name][2]


class BurnOverTheWholeWindow(Model):
    """Measures the burn rate over the SLO window, whatever the lookback."""

    def burn(self, name: str, at: int, lookback: int) -> Fraction | None:
        return super().burn(name, at, self.slos[name][3])


class TimeIgnoresWhatIsLeft(Model):
    """Divides the whole window by the burn rate, as if no budget had been spent."""

    def time_to_exhaustion(self, name: str, at: int, lookback: int) -> int:
        answer = super().time_to_exhaustion(name, at, lookback)
        speed = self.burn(name, at, lookback) if name in self.slos else None
        if answer <= 0 or not speed:
            return answer
        return math.floor(self.slos[name][3] / speed)


class TimeRoundedToNearest(Model):
    """Rounds the time to the nearest second."""

    def round_time(self, value: Fraction) -> int:
        return math.floor(value + Fraction(1, 2))


class TimeRoundedUp(Model):
    """Rounds the time up."""

    def round_time(self, value: Fraction) -> int:
        return math.ceil(value)


class OverspentGivesNegativeTime(Model):
    """Reports how long ago the budget ran out, as a negative time."""

    def spent(self, remaining: Fraction) -> int:
        return -1


class SliIsTheErrorRatio(Model):
    """Reports the share of bad requests as the indicator."""

    def sli(self, name: str, at: int) -> str:
        found = super().sli(name, at)
        return found if found == "" else self.show(1 - read(found))


class ObjectiveOfOneAllowed(Model):
    """Accepts an objective of 100%, which leaves no budget."""

    def objective_ok(self, objective: Fraction) -> bool:
        return 0 < objective <= 1


class RedefiningReplaces(Model):
    """Replaces an SLO defined twice."""

    def define_slo(self, name: str, good: str, total: str, objective: str, window: int) -> str:
        self.slos.pop(name, None)
        return super().define_slo(name, good, total, objective, window)


class RemainingNeverBelowZero(Model):
    """Clamps an overspent budget to zero."""

    def left(self, name: str, at: int) -> Fraction | None:
        found = super().left(name, at)
        return None if found is None else max(found, Fraction(0))


class RollingWindowOneSecondShort(Model):
    """Starts the window one second after at - window."""

    def window_start(self, at: int, span: int) -> int:
        return at - span + 1


# ------------------------------------------------------------------ level 4 mistakes
class FiresAtTheThreshold(Model):
    """Fires when the burn rate equals the threshold."""

    def above(self, burn: Fraction | None, threshold: Fraction) -> bool:
        return burn is not None and burn >= threshold


class LongWindowOnly(Model):
    """Ignores the short window."""

    def combine(self, long_hot: bool, short_hot: bool | None) -> bool:
        return long_hot


class ShortWindowOnly(Model):
    """Ignores the long window when there is a short one."""

    def combine(self, long_hot: bool, short_hot: bool | None) -> bool:
        return long_hot if short_hot is None else short_hot


class EitherWindowFires(Model):
    """Fires when either window burns too fast."""

    def combine(self, long_hot: bool, short_hot: bool | None) -> bool:
        return long_hot or bool(short_hot)


class NoTrafficCountsAsBurning(Model):
    """Treats a window without requests as burning without limit."""

    def above(self, burn: Fraction | None, threshold: Fraction) -> bool:
        return burn is None or burn > threshold


class TimelineStopsBeforeTheEnd(Model):
    """Leaves out the instant `end` itself."""

    def instants(self, start: int, end: int, step: int) -> range:
        return range(start, end, step)


class TimelineSortedBySeverity(Model):
    """Orders the events of one instant by severity name."""

    def order_events(self, events: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
        return sorted(events, key=lambda e: (e[0], e[2]))


class SameSeverityTwice(Model):
    """Accepts a second alert with a severity the SLO already has."""

    def add_alert(
        self, slo: str, severity: str, long_window: int, short_window: int, threshold: str
    ) -> str:
        if slo in self.slos and self.windows_ok(long_window, short_window):
            self.alerts[slo].append((severity, long_window, short_window, read(threshold)))
            return "ok"
        return super().add_alert(slo, severity, long_window, short_window, threshold)


class ShortAsLongAsTheLong(Model):
    """Accepts a short window as long as the long one."""

    def windows_ok(self, long_window: int, short_window: int) -> bool:
        return long_window > 0 and 0 <= short_window <= long_window


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, ZeroDivisionError, RuntimeError):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_hidden_cases_round_some_time_down_and_meet_a_threshold_exactly():
    """A time to exhaustion that is not a whole number of seconds, and a burn rate equal to an
    alert threshold, each appear in a hidden case."""
    fractional = equal = False
    for case in HIDDEN_CASES:
        model = Model()
        for op, arguments in zip(case["ops"][1:], case["args"][1:], strict=True):
            getattr(model, snake_case(op))(*arguments)
            if op == "timeToExhaustion" and model.time_to_exhaustion(*arguments) > 0:
                name, at, lookback = arguments
                remaining, speed = model.left(name, at), model.burn(name, at, lookback)
                assert remaining is not None
                assert speed
                fractional |= (remaining * model.slos[name][3] / speed).denominator != 1
            if op == "firing":
                slo, at = arguments
                for _, long_window, _, threshold in model.alerts.get(slo, []):
                    equal |= model.burn(slo, at, long_window) == threshold
    assert fractional
    assert equal
