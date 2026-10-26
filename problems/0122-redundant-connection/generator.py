"""Seeded inputs for redundant-connection: a random tree with a big star, plus one extra edge.

There are n nodes (at least 3, capped at 1000) under shuffled labels 1 to n. Node by node,
each new node joins the tree either as a leaf of one hub (listed hub first) or under a
random earlier node (in either orientation). One extra edge joins two nodes that are not
already neighbors, and all n edges are shuffled.

The hub-first star edges make naive union-find slow: each one links the hub's root under a
fresh leaf, growing a chain that later finds on the hub walk again, about n^2 / 4 steps.
Searching for a path before every edge is quadratic as well; union by size with path
compression stays near-linear.
"""

import random

MIN_NODES = 3
MAX_NODES = 1000
STAR_SHARE = 0.5


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, MIN_NODES), MAX_NODES)
    nodes = list(range(1, count + 1))
    rng.shuffle(nodes)
    hub = nodes[0]
    edges: list[list[int]] = []
    joined: set[frozenset[int]] = set()
    for i in range(1, count):
        node = nodes[i]
        if rng.random() < STAR_SHARE:
            edge = [hub, node]
        else:
            other = nodes[rng.randrange(i)]
            edge = [other, node] if rng.random() < 0.5 else [node, other]
        edges.append(edge)
        joined.add(frozenset(edge))
    while True:
        a, b = rng.sample(nodes, 2)
        if frozenset((a, b)) not in joined:
            break
    edges.append([a, b])
    rng.shuffle(edges)
    return {"edges": edges}


def validate(case_input: dict) -> None:
    edges = case_input["edges"]
    count = len(edges)
    assert MIN_NODES <= count <= MAX_NODES, "edge count out of range"
    assert all(len(edge) == 2 for edge in edges), "edges need two endpoints"
    assert all(1 <= node <= count for edge in edges for node in edge), "node out of range"
    assert all(a != b for a, b in edges), "no loops"
    assert len({frozenset(edge) for edge in edges}) == count, "edges must be distinct"
    root = list(range(count + 1))

    def find(x: int) -> int:
        while root[x] != x:
            x = root[x]
        return x

    cycles = 0
    for a, b in edges:
        if find(a) == find(b):
            cycles += 1
        else:
            root[find(a)] = find(b)
    assert cycles == 1, "edges must form a tree plus one extra edge"
