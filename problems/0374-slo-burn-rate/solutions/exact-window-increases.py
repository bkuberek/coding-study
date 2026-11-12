from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from math import gcd


def fraction(numerator: int, denominator: int) -> str:
    """`p/q` in lowest terms with q > 0, or `p` for a whole number."""
    if denominator < 0:
        numerator, denominator = -numerator, -denominator
    common = gcd(numerator, denominator)
    numerator, denominator = numerator // common, denominator // common
    return str(numerator) if denominator == 1 else f"{numerator}/{denominator}"


def parse_fraction(text: str) -> tuple[int, int]:
    top, _, bottom = text.partition("/")
    return int(top), int(bottom) if bottom else 1


@dataclass
class Slo:
    good: str
    total: str
    met: int
    out_of: int
    window: int

    @property
    def spare(self) -> int:
        """The error budget is spare / out_of of all requests."""
        return self.out_of - self.met


@dataclass
class Alert:
    severity: str
    long_window: int
    short_window: int
    above: int
    below: int


class SloMonitor:
    """Every counter keeps its samples in time order. The increase over a window walks the samples
    inside it and adds each step, counting a drop as a restart from zero. A histogram is one such
    counter per bucket. SLOs, burn rates and alerts are ratios of increases, kept as exact
    fractions and compared by cross-multiplying."""

    def __init__(self) -> None:
        self._times: dict[str, list[int]] = {}
        self._values: dict[str, list[int]] = {}
        self._bounds: dict[str, list[int]] = {}
        self._slos: dict[str, Slo] = {}
        self._alerts: dict[str, list[Alert]] = {}

    # Level 1
    def scrape(self, series: str, timestamp: int, value: int) -> str:
        times = self._times.setdefault(series, [])
        if times and timestamp <= times[-1]:
            return "out-of-order"
        times.append(timestamp)
        self._values.setdefault(series, []).append(value)
        return "ok"

    def scrape_series(self, series: str, start: int, step: int, values: list[int]) -> int:
        return sum(self.scrape(series, start + i * step, v) == "ok" for i, v in enumerate(values))

    def _window(self, series: str, start: int, end: int) -> list[tuple[int, int]]:
        times = self._times.get(series, [])
        low, high = bisect_left(times, start), bisect_right(times, end)
        return list(zip(times[low:high], self._values[series][low:high], strict=True)) if times else []

    def increase(self, series: str, start: int, end: int) -> int:
        samples = self._window(series, start, end)
        if len(samples) < 2:
            return -1
        total = 0
        for (_, before), (_, after) in zip(samples, samples[1:], strict=False):
            total += after - before if after >= before else after
        return total

    def rate(self, series: str, start: int, end: int) -> str:
        samples = self._window(series, start, end)
        if len(samples) < 2:
            return ""
        return fraction(self.increase(series, start, end), samples[-1][0] - samples[0][0])

    def resets(self, series: str, start: int, end: int) -> int:
        samples = self._window(series, start, end)
        return sum(after < before for (_, before), (_, after) in zip(samples, samples[1:], strict=False))

    # Level 2
    def scrape_histogram(self, name: str, timestamp: int, bounds: list[int], counts: list[int]) -> str:
        times = self._times.get(f"{name}:le=inf", [])
        if times and timestamp <= times[-1]:
            return "out-of-order"
        self._bounds[name] = bounds
        for bound, count in zip([*map(str, bounds), "inf"], counts, strict=True):
            self.scrape(f"{name}:le={bound}", timestamp, count)
        return "ok"

    def _buckets(self, name: str, start: int, end: int) -> list[int] | None:
        """The increase of every bucket over the window, or None when the window has no requests."""
        if name not in self._bounds:
            return None
        labels = [*map(str, self._bounds[name]), "inf"]
        counts = [self.increase(f"{name}:le={label}", start, end) for label in labels]
        return counts if counts[-1] > 0 else None

    def fraction_within(self, name: str, threshold: int, start: int, end: int) -> str:
        counts = self._buckets(name, start, end)
        if counts is None or threshold not in self._bounds[name]:
            return ""
        return fraction(counts[self._bounds[name].index(threshold)], counts[-1])

    def quantile(self, name: str, q: str, start: int, end: int) -> str:
        counts = self._buckets(name, start, end)
        if counts is None:
            return ""
        top, bottom = parse_fraction(q)
        bounds = self._bounds[name]
        # The rank is q * total; the first bucket whose count reaches it holds the quantile.
        index = next(i for i, count in enumerate(counts) if count * bottom >= top * counts[-1])
        if index == len(bounds):
            return str(bounds[-1])
        lower = bounds[index - 1] if index > 0 else 0
        before = counts[index - 1] if index > 0 else 0
        inside = counts[index] - before
        numerator = lower * bottom * inside + (bounds[index] - lower) * (top * counts[-1] - bottom * before)
        return fraction(numerator, bottom * inside)

    # Level 3
    def define_slo(self, name: str, good_series: str, total_series: str, objective: str, window: int) -> str:
        if name in self._slos:
            return "duplicate"
        met, out_of = parse_fraction(objective)
        if not 0 < met < out_of:
            return "bad-objective"
        self._slos[name] = Slo(good_series, total_series, met, out_of, window)
        self._alerts[name] = []
        return "ok"

    def _counts(self, slo: Slo, at: int, span: int) -> tuple[int, int] | None:
        """(bad, total) over [at - span, at], or None without requests."""
        total = self.increase(slo.total, at - span, at)
        good = self.increase(slo.good, at - span, at)
        if total <= 0 or good < 0:
            return None
        return total - good, total

    def sli(self, name: str, at: int) -> str:
        slo = self._slos.get(name)
        counts = self._counts(slo, at, slo.window) if slo else None
        if counts is None:
            return ""
        bad, total = counts
        return fraction(total - bad, total)

    def _left(self, slo: Slo, at: int) -> tuple[int, int] | None:
        """The share of the budget left, as (numerator, denominator)."""
        counts = self._counts(slo, at, slo.window)
        if counts is None:
            return None
        bad, total = counts
        return total * slo.spare - bad * slo.out_of, total * slo.spare

    def budget_remaining(self, name: str, at: int) -> str:
        slo = self._slos.get(name)
        left = self._left(slo, at) if slo else None
        return "" if left is None else fraction(*left)

    def burn_rate(self, name: str, at: int, lookback: int) -> str:
        slo = self._slos.get(name)
        counts = self._counts(slo, at, lookback) if slo else None
        if slo is None or counts is None:
            return ""
        bad, total = counts
        return fraction(bad * slo.out_of, total * slo.spare)

    def time_to_exhaustion(self, name: str, at: int, lookback: int) -> int:
        slo = self._slos.get(name)
        left = self._left(slo, at) if slo else None
        if slo is None or left is None:
            return -1
        if left[0] <= 0:
            return 0
        recent = self._counts(slo, at, lookback)
        if recent is None or recent[0] == 0:
            return -1
        bad, total = self._counts(slo, at, slo.window)  # type: ignore[misc]
        recent_bad, recent_total = recent
        # remaining * window / burn rate, with every product below 2^63.
        numerator = slo.window * (total * slo.spare - bad * slo.out_of) * recent_total
        return numerator // (total * recent_bad * slo.out_of)

    # Level 4
    def add_alert(self, slo: str, severity: str, long_window: int, short_window: int, threshold: str) -> str:
        if slo not in self._slos:
            return "unknown-slo"
        if any(alert.severity == severity for alert in self._alerts[slo]):
            return "duplicate"
        if long_window <= 0 or short_window < 0 or short_window >= long_window:
            return "bad-windows"
        top, bottom = parse_fraction(threshold)
        self._alerts[slo].append(Alert(severity, long_window, short_window, top, bottom))
        return "ok"

    def _burns_above(self, slo: Slo, at: int, span: int, alert: Alert) -> bool:
        counts = self._counts(slo, at, span)
        if counts is None:
            return False
        bad, total = counts
        return bad * slo.out_of * alert.below > alert.above * total * slo.spare

    def _fires(self, slo: Slo, alert: Alert, at: int) -> bool:
        if not self._burns_above(slo, at, alert.long_window, alert):
            return False
        return alert.short_window == 0 or self._burns_above(slo, at, alert.short_window, alert)

    def firing(self, slo: str, at: int) -> list[str]:
        if slo not in self._slos:
            return []
        return [a.severity for a in self._alerts[slo] if self._fires(self._slos[slo], a, at)]

    def timeline(self, slo: str, start: int, end: int, step: int) -> list[str]:
        if slo not in self._slos:
            return []
        alerts = self._alerts[slo]
        state = [False] * len(alerts)
        events = []
        for at in range(start, end + 1, step):
            for i, alert in enumerate(alerts):
                now = self._fires(self._slos[slo], alert, at)
                if now != state[i]:
                    events.append(f"{at} {alert.severity} {'start' if now else 'stop'}")
                    state[i] = now
        return events
