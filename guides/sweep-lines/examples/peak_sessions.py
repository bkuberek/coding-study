"""A server logs sessions as [connect, disconnect) in minutes. How many sessions were open at once,
at the busiest moment? Each session becomes two events, +1 and -1, swept from left to right."""

Interval = tuple[int, int]
OPEN, CLOSE = +1, -1


def events(sessions: list[Interval]) -> list[tuple[int, int]]:
    """(time, change) pairs. Sorting them puts CLOSE (-1) before OPEN (+1) at equal times."""
    return sorted([(start, OPEN) for start, _ in sessions] + [(end, CLOSE) for _, end in sessions])


def peak(sorted_events: list[tuple[int, int]]) -> int:
    open_now = highest = 0
    for _, change in sorted_events:
        open_now += change
        highest = max(highest, open_now)
    return highest


def peak_by_brute_force(sessions: list[Interval]) -> int:
    return max(sum(start <= t < end for start, end in sessions) for t, _ in sessions)


sessions = [(0, 4), (1, 4), (2, 6), (4, 8), (5, 7), (9, 10)]
open_now = 0
for time, change in events(sessions):
    open_now += change
    print(f"t={time:>2} {'+1' if change == OPEN else '-1'} -> {open_now} open")
print("peak:", peak(events(sessions)), "| brute force:", peak_by_brute_force(sessions))

opens_first = sorted(events(sessions), key=lambda event: (event[0], -event[1]))
print("peak with opens before closes at equal times:", peak(opens_first))
