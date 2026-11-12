"""The highest temperature per 10 minutes, grouped by event time and by processing time.

A sensor was offline from minute 6 to minute 14 and uploaded what it had buffered at minute 15.
Grouping by the minute a reading happened (event time) keeps the spike at minute 7 where it
belongs; grouping by the minute it arrived (processing time) moves it into the next window.
"""

SIZE = 10
READINGS = [  # (minute it happened, minute it arrived, degrees Celsius)
    (1, 1, 20),
    (4, 4, 21),
    (7, 15, 35),
    (9, 15, 22),
    (12, 15, 23),
    (16, 16, 24),
    (18, 18, 25),
]


def window_of(minute: int) -> tuple[int, int]:
    """The tumbling window [start, end) that holds a minute."""
    start = minute - minute % SIZE
    return start, start + SIZE


def highest_by(clock: int) -> dict[tuple[int, int], int]:
    highest: dict[tuple[int, int], int] = {}
    for reading in READINGS:
        window = window_of(reading[clock])
        highest[window] = max(highest.get(window, reading[2]), reading[2])
    return dict(sorted(highest.items()))


for name, clock in (("event time", 0), ("processing time", 1)):
    windows = ", ".join(f"[{s}, {e}) max {c}" for (s, e), c in highest_by(clock).items())
    print(f"{name:>15}: {windows}")
