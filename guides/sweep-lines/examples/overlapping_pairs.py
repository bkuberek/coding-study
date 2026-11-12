"""How many pairs of sessions overlap? Every overlapping pair is counted once, at the moment the
later of the two opens: it overlaps exactly the sessions that are open at that moment."""

from itertools import combinations, combinations_with_replacement

Interval = tuple[int, int]
OPEN, CLOSE = +1, -1


def overlapping_pairs(sessions: list[Interval]) -> int:
    swept = sorted([(start, OPEN) for start, _ in sessions] + [(end, CLOSE) for _, end in sessions])
    open_now = pairs = 0
    for _, change in swept:
        if change == OPEN:
            pairs += open_now
        open_now += change
    return pairs


def overlapping_pairs_by_brute_force(sessions: list[Interval]) -> int:
    return sum(a[0] < b[1] and b[0] < a[1] for a, b in combinations(sessions, 2))


sessions = [(0, 4), (1, 4), (2, 6), (4, 8), (5, 7), (9, 10)]
by_sweep, by_pairs = overlapping_pairs(sessions), overlapping_pairs_by_brute_force(sessions)
print(f"sweep: {by_sweep} | every pair: {by_pairs}")

every_session = [(start, end) for start in range(5) for end in range(start + 1, 5)]
inputs = [
    list(chosen)
    for size in (1, 2, 3, 4)
    for chosen in combinations_with_replacement(every_session, size)
]
disagree = sum(overlapping_pairs(s) != overlapping_pairs_by_brute_force(s) for s in inputs)
print(f"{len(inputs)} small inputs, repeats allowed: the two disagree on {disagree}")
