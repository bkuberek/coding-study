"""Seeded inputs for smallest-string-with-swaps: star-shaped position groups plus extra pairs.

The string has n letters (capped at 10^5) from a random alphabet of 1 to 26 letters. The
positions are shuffled; at least half of them form one large group and the rest are split
into groups of random sizes (single positions included). Each group is a star around a hub
position, listed hub first, plus about half as many extra pairs inside the group, a few of
them repeated or joining a position to itself. Pairs are shuffled.

The hub-first star pairs grow one long chain in naive union-find, so its later finds on the
hub cost about n^2 / 2 steps in total; union by size with path compression stays
near-linear, and sorting the groups adds n log n.
"""

import random
import string

MIN_LENGTH = 1
MAX_LENGTH = 10**5
MAX_PAIRS = 10**5


def _groups(rng: random.Random, positions: list[int]) -> list[list[int]]:
    big = rng.randint((len(positions) + 1) // 2, len(positions))
    groups = [positions[:big]]
    rest = positions[big:]
    largest_small = max(1, len(positions) // 10)
    while rest:
        size = rng.randint(1, min(largest_small, len(rest)))
        groups.append(rest[:size])
        rest = rest[size:]
    return groups


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    alphabet = rng.sample(string.ascii_lowercase, rng.randint(1, 26))
    s = "".join(rng.choice(alphabet) for _ in range(length))
    positions = list(range(length))
    rng.shuffle(positions)
    star_pairs: list[list[int]] = []
    extra_pairs: list[list[int]] = []
    for group in _groups(rng, positions):
        hub = group[0]
        star_pairs.extend([hub, position] for position in group[1:])
        for _ in range(len(group) // 2):
            if rng.random() < 0.05:
                position = rng.choice(group)
                extra_pairs.append([position, position])
            else:
                extra_pairs.append(rng.sample(group, 2) if len(group) >= 2 else [hub, hub])
    if extra_pairs and rng.random() < 0.5:
        extra_pairs.append(list(rng.choice(extra_pairs)))
    pairs = star_pairs + extra_pairs[: MAX_PAIRS - len(star_pairs)]
    rng.shuffle(pairs)
    return {"s": s, "pairs": pairs}


def validate(case_input: dict) -> None:
    s, pairs = case_input["s"], case_input["pairs"]
    assert MIN_LENGTH <= len(s) <= MAX_LENGTH, "length out of range"
    assert set(s) <= set(string.ascii_lowercase), "s must be lowercase letters"
    assert len(pairs) <= MAX_PAIRS, "too many pairs"
    assert all(len(pair) == 2 for pair in pairs), "pairs need two positions"
    assert all(0 <= position < len(s) for pair in pairs for position in pair), "position out of range"
