"""Seeded connected networks for critical-connections.

`n` is the number of servers (2 to 2000). The servers are split into groups; each group of
three or more is closed into a ring with a few random chords, which makes all its cables
non-critical, and groups of one or two stay as chains. The groups are then linked by a random
tree of single cables (all critical). The total stays below about 1.5n cables. Server numbers
are shuffled and each cable's two ends are listed in random order.
"""

import random

MAX_SERVERS = 2000


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 2), MAX_SERVERS)
    servers = list(range(count))
    rng.shuffle(servers)
    groups: list[list[int]] = []
    index = 0
    while index < count:
        size = min(count - index, rng.choice([1, 1, 2, 3, 4, 6, 10, 25]))
        groups.append(servers[index : index + size])
        index += size
    cables: set[tuple[int, int]] = set()

    def link(a: int, b: int) -> None:
        cables.add((min(a, b), max(a, b)))

    for group in groups:
        for a, b in zip(group, group[1:]):
            link(a, b)
        if len(group) >= 3:
            link(group[-1], group[0])
            for _ in range(rng.randint(0, len(group) // 3)):
                a, b = rng.sample(group, 2)
                link(a, b)
    for position in range(1, len(groups)):
        other = groups[rng.randrange(position)]
        link(rng.choice(groups[position]), rng.choice(other))
    connections = [[a, b] if rng.random() < 0.5 else [b, a] for a, b in sorted(cables)]
    rng.shuffle(connections)
    return {"n": count, "connections": connections}


def validate(case_input: dict) -> None:
    n, connections = case_input["n"], case_input["connections"]
    assert 2 <= n <= MAX_SERVERS, "server count out of range"
    assert n - 1 <= len(connections) <= 5000, "cable count out of range"
    pairs = set()
    adjacency: list[list[int]] = [[] for _ in range(n)]
    for a, b in connections:
        assert 0 <= a < n and 0 <= b < n and a != b, "bad cable"
        pairs.add((min(a, b), max(a, b)))
        adjacency[a].append(b)
        adjacency[b].append(a)
    assert len(pairs) == len(connections), "a cable appears twice"
    seen = {0}
    stack = [0]
    while stack:
        for nxt in adjacency[stack.pop()]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    assert len(seen) == n, "the network is not connected"
