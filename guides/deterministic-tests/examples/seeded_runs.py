"""Random inputs, made repeatable: every run gets its own seed, and a failure reports it.

split_teams shuffles the players and deals them into two teams. It has a bug: with an odd number
of players, the last one is left out. A test that draws team sizes at random finds the bug, and
because each run has a recorded seed, the same failure can be replayed exactly.
"""

import random


def split_teams(players: list[str], rng: random.Random) -> tuple[list[str], list[str]]:
    shuffled = players[:]
    rng.shuffle(shuffled)
    half = len(shuffled) // 2
    return shuffled[:half], shuffled[half:2 * half]  # bug: drops the odd one out


def check(seed: int) -> str | None:
    """One run of the test: None when it passes, a description when it fails."""
    rng = random.Random(seed)
    size = 2 + int(rng.random() * 7)  # 2 to 8 players
    players = [f"p{i}" for i in range(size)]
    first, second = split_teams(players, rng)
    if sorted(first + second) != sorted(players):
        return f"{size} players in, {len(first) + len(second)} placed"
    return None


failures = {seed: failure for seed in range(1, 21) if (failure := check(seed))}
print(f"20 runs, {len(failures)} failed, with seeds {sorted(failures)}")
seed = min(failures)
print(f"seed {seed}: {failures[seed]}")
print("replaying seed", seed, "fails the same way:", check(seed) == failures[seed])
