"""Seeded connected graphs for clone-graph.

`n` is the number of nodes (capped at 2000). A random spanning tree keeps the graph
connected: each new node attaches to one of the last few nodes added, which makes long
paths and so deep recursions likely. Then up to `n` extra edges between random distinct
pairs add cycles (no self-loops, no repeated edges, at most 100 neighbors per node). Node
values are a random relabeling of 1..n, and every neighbor list is shuffled, so neighbor
order is arbitrary and must be preserved by the copy.
"""

import random

MAX_NODES = 2000
MAX_DEGREE = 100
RECENT = 5


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_NODES)
    edges: set[tuple[int, int]] = set()
    for node in range(1, count):
        parent = rng.randint(max(0, node - RECENT), node - 1)
        edges.add((parent, node))
    degree = [0] * count
    for a, b in edges:
        degree[a] += 1
        degree[b] += 1
    for _ in range(rng.randint(0, count)):
        a, b = rng.randrange(count), rng.randrange(count)
        if a == b:
            continue
        pair = (min(a, b), max(a, b))
        if pair in edges or degree[a] >= MAX_DEGREE or degree[b] >= MAX_DEGREE:
            continue
        edges.add(pair)
        degree[a] += 1
        degree[b] += 1
    labels = list(range(1, count + 1))
    rng.shuffle(labels)
    adjacency: list[list[int]] = [[] for _ in range(count)]
    for a, b in sorted(edges):
        adjacency[labels[a] - 1].append(labels[b])
        adjacency[labels[b] - 1].append(labels[a])
    for neighbors in adjacency:
        rng.shuffle(neighbors)
    return {"node": adjacency}


def validate(case_input: dict) -> None:
    adjacency = case_input["node"]
    count = len(adjacency)
    assert count <= MAX_NODES, "too many nodes"
    links = set()
    for index, neighbors in enumerate(adjacency, start=1):
        assert len(neighbors) <= MAX_DEGREE, "too many neighbors"
        assert len(set(neighbors)) == len(neighbors), "repeated edge"
        for neighbor in neighbors:
            assert 1 <= neighbor <= count and neighbor != index, "bad neighbor"
            links.add((index, neighbor))
    assert all((b, a) in links for a, b in links), "edges are not symmetric"
    if count:
        seen = {1}
        stack = [1]
        while stack:
            for neighbor in adjacency[stack.pop() - 1]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        assert len(seen) == count, "graph is not connected"
