"""stream-windows promises that its hidden cases catch the classic mistakes of windowed
aggregation: windows that include their end, rows in the wrong order, hopping windows that skip
the ones starting before 0 or ignore gaps, sessions merged when they only touch or measured from
the wrong event, a watermark that goes down or below 0, windows emitted a step late, lateness read
per event instead of per window, corrections without retractions, the wrong grace boundary, and a
side output or views that forget dropped events. These tests replay every case against a model
of the engine written from the statement, which must give every expected output, and against that
model with one mistake planted at a time, which some hidden case must fail. The model recomputes
every answer from the events it has seen instead of keeping running totals. A mistake that
crashes fails its case, as a thrown exception does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0332-stream-windows"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

Event = tuple[int, int, int]
Window = tuple[int, int]


class Model:
    """The engine as the statement words it, one rule per method. The views filter the event list
    for each candidate window, sessions merge overlapping windows until none overlap, and the
    stream recomputes its watermark and its window totals from the events it has seen."""

    def __init__(self) -> None:
        self.events: list[Event] = []
        self.size = 0
        self.lateness = 0
        self.grace = 0
        self.stream_times: list[int] = []
        self.joined: list[Event] = []
        self.results: dict[Window, tuple[int, int]] = {}
        self.out: list[list[int]] = []
        self.side: list[list[int]] = []
        self.firsts = 0
        self.corrections = 0

    # --- shared rules
    def holds(self, start: int, end: int, time: int) -> bool:
        return start <= time < end

    def tumbling_start(self, time: int, size: int) -> int:
        return time // size * size

    def order(self, rows: list[list[int]]) -> list[list[int]]:
        return sorted(rows, key=lambda row: (row[1], row[0]))

    def totals(self, events: list[Event], key: int, start: int, end: int) -> tuple[int, int]:
        values = [v for k, t, v in events if k == key and self.holds(start, end, t)]
        return len(values), sum(values)

    def view(self, windows: set[tuple[int, int, int]]) -> list[list[int]]:
        rows = []
        for key, start, end in windows:
            count, total = self.totals(self.events, key, start, end)
            if count:
                rows.append([key, start, end, count, total])
        return self.order(rows)

    # --- level 1
    def add(self, key: int, time: int, value: int) -> None:
        self.events.append((key, time, value))
        if self.size:
            self.stream(key, time, value)

    def tumbling(self, size: int) -> list[list[int]]:
        windows = set()
        for key, time, _ in self.events:
            start = self.tumbling_start(time, size)
            windows.add((key, start, start + size))
        return self.view(windows)

    # --- level 2
    def hopping_starts(self, time: int, size: int, slide: int) -> list[int]:
        first = (time - size) // slide
        return [k * slide for k in range(first, time // slide + 1)]

    def hopping(self, size: int, slide: int) -> list[list[int]]:
        windows = {
            (key, start, start + size)
            for key, time, _ in self.events
            for start in self.hopping_starts(time, size, slide)
        }
        return self.view(windows)

    def overlap(self, a: list[int], b: list[int]) -> bool:
        return a[0] < b[1] and b[0] < a[1]

    def sessions(self, gap: int) -> list[list[int]]:
        rows = []
        for key in {k for k, _, _ in self.events}:
            spans = [[t, t + gap, 1, v] for k, t, v in self.events if k == key]
            merged = True
            while merged:
                merged = False
                for i in range(len(spans)):
                    for j in range(i + 1, len(spans)):
                        a, b = spans[i], spans[j]
                        if self.overlap(a, b):
                            spans[i] = [min(a[0], b[0]), max(a[1], b[1]), a[2] + b[2], a[3] + b[3]]
                            del spans[j]
                            merged = True
                            break
                    if merged:
                        break
            rows += [[key, *span] for span in spans]
        return self.order(rows)

    # --- level 3
    def configure(self, size: int, lateness: int) -> None:
        self.size = size
        self.lateness = lateness

    def watermark(self) -> int:
        return max([0] + [t - self.lateness for t in self.stream_times])

    def is_late(self, end: int, time: int) -> bool:
        return end <= self.watermark()

    def due(self, end: int) -> bool:
        return end <= self.watermark()

    def stream_windows(self) -> set[Window]:
        return {(self.tumbling_start(t, self.size), k) for k, t, _ in self.joined}

    def row(self, window: Window) -> list[int]:
        start, key = window
        count, total = self.totals(self.joined, key, start, start + self.size)
        return [key, start, start + self.size, count, total]

    def emit_due(self) -> None:
        due = [
            w for w in self.stream_windows() if w not in self.results and self.due(w[0] + self.size)
        ]
        for window in self.order_windows(due):
            row = self.row(window)
            self.out.append(row)
            self.results[window] = (row[3], row[4])
            self.firsts += 1

    def order_windows(self, windows: list[Window]) -> list[Window]:
        return sorted(windows)

    def pending(self) -> list[list[int]]:
        return [self.row(w) for w in self.order_windows(list(self.open_windows()))]

    def open_windows(self) -> set[Window]:
        return {w for w in self.stream_windows() if w not in self.results}

    def poll(self) -> list[list[int]]:
        out, self.out = self.out, []
        return out

    # --- level 4
    def allow_updates(self, grace: int) -> None:
        self.grace = grace

    def correctable(self, end: int) -> bool:
        return self.watermark() < end + self.grace

    def retraction(self, window: Window, previous: tuple[int, int]) -> list[int]:
        start, key = window
        return [key, start, start + self.size, -previous[0], -previous[1]]

    def correct(self, window: Window) -> None:
        row = self.row(window)
        previous = self.results.get(window)
        if previous is None:
            self.firsts += 1
        else:
            self.out.append(self.retraction(window, previous))
            self.corrections += 1
        self.out.append(row)
        self.results[window] = (row[3], row[4])

    def drop(self, key: int, time: int, value: int) -> None:
        self.side.append([key, time, value])

    def stream(self, key: int, time: int, value: int) -> None:
        start = self.tumbling_start(time, self.size)
        end = start + self.size
        if not self.is_late(end, time):
            self.joined.append((key, time, value))
        elif self.correctable(end):
            self.joined.append((key, time, value))
            self.correct((start, key))
        else:
            self.drop(key, time, value)
        self.stream_times.append(time)
        self.emit_due()

    def dropped(self) -> list[list[int]]:
        return [list(row) for row in self.side]

    def stats(self) -> list[int]:
        return [self.firsts, self.corrections, len(self.side)]


# ------------------------------------------------------------------ level 1 mistakes
class WindowIncludesItsEnd(Model):
    """Puts an event at a multiple of the size in the window that ends there."""

    def tumbling_start(self, time: int, size: int) -> int:
        return (time - 1) // size * size if time % size == 0 and time > 0 else time // size * size

    def holds(self, start: int, end: int, time: int) -> bool:
        return start < time <= end


class SortedByKeyFirst(Model):
    """Orders rows by key, then start."""

    def order(self, rows: list[list[int]]) -> list[list[int]]:
        return sorted(rows)


class StartIsTheWindowNumber(Model):
    """Reports the window's number instead of its start time."""

    def view(self, windows: set[tuple[int, int, int]]) -> list[list[int]]:
        rows = super().view(windows)
        return [[k, s // (e - s), s // (e - s) + e - s, c, t] for k, s, e, c, t in rows]


class EndIsTheLastMoment(Model):
    """Writes the end as the last time inside the window."""

    def view(self, windows: set[tuple[int, int, int]]) -> list[list[int]]:
        return [[k, s, e - 1, c, t] for k, s, e, c, t in super().view(windows)]


class ZeroSumWindowsSkipped(Model):
    """Leaves out a window whose values add up to zero."""

    def view(self, windows: set[tuple[int, int, int]]) -> list[list[int]]:
        return [row for row in super().view(windows) if row[4] != 0]


class ViewCoversOnlyNewEvents(Model):
    """Forgets the events a previous view already grouped."""

    def tumbling(self, size: int) -> list[list[int]]:
        rows = super().tumbling(size)
        self.events = []
        return rows


class CountsDistinctTimes(Model):
    """Counts each time once, even when two events of a key share it."""

    def totals(self, events: list[Event], key: int, start: int, end: int) -> tuple[int, int]:
        values = [v for k, t, v in events if k == key and self.holds(start, end, t)]
        times = {t for k, t, v in events if k == key and self.holds(start, end, t)}
        return len(times), sum(values)


# ------------------------------------------------------------------ level 2 mistakes
class HoppingStartsAtZero(Model):
    """Skips the hopping windows that start before 0."""

    def hopping_starts(self, time: int, size: int, slide: int) -> list[int]:
        return [s for s in super().hopping_starts(time, size, slide) if s >= 0]


class HoppingCountByDivision(Model):
    """Puts every event in size // slide windows, counting back from the latest start."""

    def hopping_starts(self, time: int, size: int, slide: int) -> list[int]:
        latest = time // slide * slide
        return [latest - i * slide for i in range(max(1, size // slide))]


class HoppingIgnoresGaps(Model):
    """Puts an event in the latest window that starts before it, even past that window's end."""

    def hopping(self, size: int, slide: int) -> list[list[int]]:
        windows = set()
        for key, time, _ in self.events:
            starts = self.hopping_starts(time, size, slide) or [time // slide * slide]
            windows |= {(key, s, s + size) for s in starts}
        rows = []
        for key, start, end in windows:
            values = [
                v for k, t, v in self.events if k == key and start <= t < max(end, start + slide)
            ]
            rows.append([key, start, end, len(values), sum(values)])
        return self.order(rows)


class HoppingIncludesItsEnd(Model):
    """Lets a hopping window hold the time at its end."""

    def hopping_starts(self, time: int, size: int, slide: int) -> list[int]:
        return [k * slide for k in range((time - size) // slide, time // slide + 1)]

    def hopping(self, size: int, slide: int) -> list[list[int]]:
        windows = {
            (key, start, start + size)
            for key, time, _ in self.events
            for start in self.hopping_starts(time, size, slide)
        }
        rows = []
        for key, start, end in windows:
            values = [v for k, t, v in self.events if k == key and start <= t <= end]
            if values:
                rows.append([key, start, end, len(values), sum(values)])
        return self.order(rows)


class SessionsMergeWhenTouching(Model):
    """Merges two session windows that only touch."""

    def overlap(self, a: list[int], b: list[int]) -> bool:
        return a[0] <= b[1] and b[0] <= a[1]


class SessionsInArrivalOrder(Model):
    """Builds sessions in the order the events arrived."""

    def sessions(self, gap: int) -> list[list[int]]:
        rows: list[list[int]] = []
        current: dict[int, list[int]] = {}
        for key, time, value in self.events:
            row = current.get(key)
            if row is not None and row[1] <= time < row[2]:
                row[2] = time + gap
                row[3] += 1
                row[4] += value
            else:
                row = [key, time, time + gap, 1, value]
                current[key] = row
                rows.append(row)
        return self.order(rows)


class SessionGapFromFirstEvent(Model):
    """Lets a session end gap after its first event."""

    def sessions(self, gap: int) -> list[list[int]]:
        rows = []
        for key in {k for k, _, _ in self.events}:
            row: list[int] = []
            for time, value in sorted((t, v) for k, t, v in self.events if k == key):
                if row and time < row[1] + gap:
                    row[3] += 1
                    row[4] += value
                    row[2] = time + gap
                else:
                    row = [key, time, time + gap, 1, value]
                    rows.append(row)
        return self.order(rows)


class SessionEndsAtLastEvent(Model):
    """Ends a session at its last event instead of gap after it."""

    def sessions(self, gap: int) -> list[list[int]]:
        return self.order([[k, s, e - gap + 1, c, t] for k, s, e, c, t in super().sessions(gap)])


class SessionsByKeyFirst(Model):
    """Orders sessions by key, then start."""

    def sessions(self, gap: int) -> list[list[int]]:
        return sorted(super().sessions(gap))


# ------------------------------------------------------------------ level 3 mistakes
class WatermarkFromLatestEvent(Model):
    """Takes the watermark from the most recent event, which can move it back."""

    def watermark(self) -> int:
        if not self.stream_times:
            return 0
        return max(0, self.stream_times[-1] - self.lateness)


class WatermarkBelowZero(Model):
    """Lets the watermark start below 0."""

    def watermark(self) -> int:
        if not self.stream_times:
            return 0
        return max(self.stream_times) - self.lateness


class EmitsOnlyPastTheEnd(Model):
    """Waits for the watermark to pass beyond a window's end."""

    def due(self, end: int) -> bool:
        return end < self.watermark()


class EmitsByKeyFirst(Model):
    """Emits the due windows by key, then start."""

    def order_windows(self, windows: list[Window]) -> list[Window]:
        return sorted(windows, key=lambda w: (w[1], w[0]))


class PollKeepsItsRows(Model):
    """Hands the same rows over on every poll."""

    def poll(self) -> list[list[int]]:
        return list(self.out)


class PendingKeepsEmitted(Model):
    """Lists the emitted windows as pending too."""

    def open_windows(self) -> set[Window]:
        return self.stream_windows()


class LateMeansBehindTheWatermark(Model):
    """Treats every event behind the watermark as late, even when its window is open."""

    def is_late(self, end: int, time: int) -> bool:
        return time < self.watermark() or super().is_late(end, time)


class StreamForgetsOutOfOrderEvents(Model):
    """Lets an event join only a window at or after the newest event's window."""

    def stream(self, key: int, time: int, value: int) -> None:
        newest = max(self.stream_times, default=0)
        if self.tumbling_start(time, self.size) < self.tumbling_start(newest, self.size):
            self.stream_times.append(time)
            self.emit_due()
            return
        super().stream(key, time, value)


# ------------------------------------------------------------------ level 4 mistakes
class CorrectionWithoutRetraction(Model):
    """Emits the new result of a corrected window without retracting the old one."""

    def retraction(self, window: Window, previous: tuple[int, int]) -> list[int]:
        return []

    def correct(self, window: Window) -> None:
        super().correct(window)
        self.out = [row for row in self.out if row]


class RetractsTheFirstResult(Model):
    """Retracts the first result of a window instead of the last one."""

    def __init__(self) -> None:
        super().__init__()
        self.first_results: dict[Window, tuple[int, int]] = {}

    def correct(self, window: Window) -> None:
        if window in self.results:
            self.first_results.setdefault(window, self.results[window])
            previous = self.first_results[window]
            self.out.append(self.retraction(window, previous))
            row = self.row(window)
            self.out.append(row)
            self.results[window] = (row[3], row[4])
            self.corrections += 1
        else:
            super().correct(window)
            self.first_results[window] = self.results[window]


class GraceBoundaryInclusive(Model):
    """Keeps a window correctable while the watermark equals its end plus grace."""

    def correctable(self, end: int) -> bool:
        return self.watermark() <= end + self.grace


class GraceIgnored(Model):
    """Drops every late event, whatever the grace."""

    def correctable(self, end: int) -> bool:
        return False


class NeverForgetsWindows(Model):
    """Corrects an emitted window however far the watermark has moved."""

    def correctable(self, end: int) -> bool:
        return self.grace > 0 or super().correctable(end)


class FirstLateResultRetractsZero(Model):
    """Retracts an empty result before the first result of a window never emitted."""

    def correct(self, window: Window) -> None:
        self.results.setdefault(window, (0, 0))
        super().correct(window)


class FirstLateResultIsAnUpdate(Model):
    """Counts the first result of a late window as a correction."""

    def correct(self, window: Window) -> None:
        before = window in self.results
        super().correct(window)
        if not before:
            self.firsts -= 1
            self.corrections += 1


class DroppedRowHoldsTheWindow(Model):
    """Writes the window start instead of the event time in the side output."""

    def drop(self, key: int, time: int, value: int) -> None:
        self.side.append([key, self.tumbling_start(time, self.size), value])


class DroppedEmptiesTheSideOutput(Model):
    """Hands each dropped event over once."""

    def dropped(self) -> list[list[int]]:
        rows = super().dropped()
        self.dropped_before = getattr(self, "dropped_before", 0) + len(rows)
        self.side = []
        return rows

    def stats(self) -> list[int]:
        return [self.firsts, self.corrections, getattr(self, "dropped_before", 0) + len(self.side)]


class ViewsForgetDroppedEvents(Model):
    """Removes a dropped event from the batch views too."""

    def drop(self, key: int, time: int, value: int) -> None:
        super().drop(key, time, value)
        self.events.remove((key, time, value))


class EmittedCountsCorrections(Model):
    """Counts every row emitted, corrections included, as a first result."""

    def stats(self) -> list[int]:
        firsts, corrections, dropped = super().stats()
        return [firsts + corrections, corrections, dropped]


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
    except (IndexError, KeyError, ValueError, TypeError, ZeroDivisionError):
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


def test_no_level_3_case_has_a_late_event():
    for case in CASES:
        if case["level"] == 3:
            model = Model()
            for op, arguments in zip(case["ops"][1:], case["args"][1:], strict=True):
                getattr(model, snake_case(op))(*arguments)
            assert model.stats() == [model.firsts, 0, 0], case["id"]
