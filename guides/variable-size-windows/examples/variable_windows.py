"""Grow on the right, shrink on the left: the longest and the shortest stretch that obey a rule."""

from itertools import product


def longest_within(durations: list[int], budget: int, trace: bool = False) -> int:
    """The most consecutive songs whose total length is at most `budget`."""
    left = total = best = 0
    for right, duration in enumerate(durations):
        total += duration  # grow: song `right` enters
        while total > budget:  # shrink until the rule holds again
            total -= durations[left]
            left += 1
        best = max(best, right - left + 1)  # the longest window that ends at `right`
        if trace:
            print(f"  right={right} left={left} {durations[left:right + 1]} total={total} best={best}")
    return best


def shortest_with_artists(playlist: list[int], wanted: int) -> int:
    """The fewest consecutive songs by at least `wanted` different artists, or 0."""
    counts: dict[int, int] = {}  # songs per artist in the window
    left = 0
    best = len(playlist) + 1
    for right, artist in enumerate(playlist):
        counts[artist] = counts.get(artist, 0) + 1  # grow
        while len(counts) >= wanted:  # the rule holds: record, then try a shorter window
            best = min(best, right - left + 1)
            leaving = playlist[left]
            counts[leaving] -= 1
            if counts[leaving] == 0:
                del counts[leaving]
            left += 1
    return best if best <= len(playlist) else 0


def every_stretch(values):
    return [values[start:end] for start in range(len(values)) for end in range(start + 1, len(values) + 1)]


songs = [4, 2, 6, 3, 1, 5, 1]
print("longest run of", songs, "within 10 minutes")
print("window:", longest_within(songs, 10, trace=True))
print("every stretch:", max(len(s) for s in every_stretch(songs) if sum(s) <= 10))

artists = [1, 2, 2, 1, 1, 3, 3, 2]
print("fewest songs in a row by 3 artists in", artists, "->", shortest_with_artists(artists, 3))

cases = disagreements = 0
for size in range(7):
    for values in product(range(4), repeat=size):  # every list of 0 to 6 values from 0 to 3
        stretches = every_stretch(list(values))
        for budget in range(9):
            cases += 1
            brute = max((len(s) for s in stretches if sum(s) <= budget), default=0)
            disagreements += longest_within(list(values), budget) != brute
        for wanted in range(1, 5):
            cases += 1
            lengths = [len(s) for s in stretches if len(set(s)) >= wanted]
            disagreements += shortest_with_artists(list(values), wanted) != min(lengths, default=0)
print(f"against every stretch: {cases} cases, {disagreements} disagreements")

mixed = [5, -4, 1]  # a negative value: the rule is no longer kept by shrinking
print("with a negative value, window:", longest_within(mixed, 3),
      "| every stretch:", max(len(s) for s in every_stretch(mixed) if sum(s) <= 3))
