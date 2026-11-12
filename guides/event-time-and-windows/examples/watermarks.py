"""One stream, two watermarks: when each 10-minute window is reported, and what arrives too late.

The watermark trails the latest event time seen by a fixed bound. A window is reported once the
watermark reaches its end; a reading whose window has already been reported is dropped. A small
bound reports sooner and drops more; a larger one waits longer and drops less.
"""

SIZE = 10
READINGS = [  # (event time, value), in the order they arrive
    (2, 18),
    (5, 22),
    (11, 19),
    (7, 31),
    (14, 20),
    (21, 17),
    (9, 40),
    (25, 16),
    (32, 15),
]


def run(bound: int) -> None:
    watermark = 0
    highest: dict[int, int] = {}  # window start -> highest value so far, for windows not reported
    dropped = []
    print(f"bound {bound}:")
    for time, value in READINGS:
        start = time - time % SIZE
        if start + SIZE <= watermark:  # its window was already reported
            dropped.append((time, value))
            continue
        highest[start] = max(highest.get(start, value), value)
        watermark = max(watermark, time - bound)
        for done in sorted(s for s in highest if s + SIZE <= watermark):
            print(f"  after {time:>2}, watermark {watermark:>2}: "
                  f"[{done}, {done + SIZE}) max {highest.pop(done)}")
    print(f"  dropped {dropped}, still open {sorted(highest)}")


run(0)
run(5)
