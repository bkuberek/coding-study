"""Seeded inputs for count-connected-components: star-shaped components plus extra edges.

There are n nodes (capped at 2000) under shuffled labels. At least half of them form one
large component and the rest are split into components of random sizes (single nodes
included). Each component is a star around a hub, listed hub first, plus about half as
many extra edges between its own nodes.

The hub-first star edges are what makes naive union-find slow: linking the hub's root under
each new leaf grows one long chain, and every later find on the hub walks it, about V^2 / 2
steps in total. Union by size keeps the trees shallow and depth-first search does not care,
so both stay linear. Edges are distinct, never loops, and shuffled.
"""

import random

MIN_NODES = 1
MAX_NODES = 2000
MAX_EDGES = 5000


def _components(rng: random.Random, nodes: list[int]) -> list[list[int]]:
    big = rng.randint((len(nodes) + 1) // 2, len(nodes))
    groups = [nodes[:big]]
    rest = nodes[big:]
    largest_small = max(1, len(nodes) // 10)
    while rest:
        size = rng.randint(1, min(largest_small, len(rest)))
        groups.append(rest[:size])
        rest = rest[size:]
    return groups


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, MIN_NODES), MAX_NODES)
    nodes = list(range(count))
    rng.shuffle(nodes)
    star_edges: list[list[int]] = []
    extra_edges: list[list[int]] = []
    seen: set[frozenset[int]] = set()
    for group in _components(rng, nodes):
        hub = group[0]
        for leaf in group[1:]:
            star_edges.append([hub, leaf])
            seen.add(frozenset((hub, leaf)))
        if len(group) >= 3:
            for _ in range(len(group) // 2):
                a, b = rng.sample(group, 2)
                if frozenset((a, b)) not in seen:
                    seen.add(frozenset((a, b)))
                    extra_edges.append([a, b])
    edges = star_edges + extra_edges[: MAX_EDGES - len(star_edges)]
    rng.shuffle(edges)
    return {"n": count, "edges": edges}


def validate(case_input: dict) -> None:
    count, edges = case_input["n"], case_input["edges"]
    assert MIN_NODES <= count <= MAX_NODES, "node count out of range"
    assert len(edges) <= MAX_EDGES, "too many edges"
    assert all(len(edge) == 2 for edge in edges), "edges need two endpoints"
    assert all(0 <= node < count for edge in edges for node in edge), "node out of range"
    assert all(a != b for a, b in edges), "no loops"
    assert len({frozenset(edge) for edge in edges}) == len(edges), "edges must be distinct"
