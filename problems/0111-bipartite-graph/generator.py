"""Seeded graphs for bipartite-graph.

`n` is the number of nodes (capped at 10^4). Every node gets a hidden team. Most nodes join
one large piece: each new node links to a random earlier node of the other team, then extra
edges between the teams add even cycles (up to about 2n edges in total). A few nodes stay in
small separate pieces or alone. Neighbor lists are shuffled.

Below UNIFORM_FROM nodes the proportions vary by seed: up to a tenth of the nodes are loners,
up to n extra edges are added, and with probability one half one edge inside a team closes an
odd cycle in the large piece, which makes the answer false.

From UNIFORM_FROM nodes on (the bench ladder), every graph has the same shape: a twentieth of
the nodes are loners, n / 2 extra edges are added, and the graph is always bipartite, so both
references visit every node and edge instead of stopping at a conflict that some seeds would
reach early and others late.
"""

import random

MAX_NODES = 10**4
UNIFORM_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_NODES)
    team = [rng.randrange(2) for _ in range(count)]
    edges: set[tuple[int, int]] = set()
    main = list(range(count))
    rng.shuffle(main)
    uniform = count >= UNIFORM_FROM
    loners = set(main[: count // 20 if uniform else rng.randint(0, max(0, count // 10))])
    joined: list[list[int]] = [[], []]
    for node in main:
        if node in loners:
            continue
        other = joined[1 - team[node]]
        if other:
            edges.add(_pair(node, rng.choice(other)))
        joined[team[node]].append(node)
    extra = count // 2 if uniform else rng.randint(0, count)
    for _ in range(extra):
        if joined[0] and joined[1]:
            edges.add(_pair(rng.choice(joined[0]), rng.choice(joined[1])))
    loner_list = sorted(loners)
    for _ in range(len(loner_list) // 2):
        a, b = rng.sample(loner_list, 2)
        if team[a] != team[b]:
            edges.add(_pair(a, b))
    if not uniform and rng.random() < 0.5:
        same = joined[0] if len(joined[0]) >= 2 else joined[1]
        if len(same) >= 2:
            a, b = rng.sample(same, 2)
            edges.add(_pair(a, b))
    graph: list[list[int]] = [[] for _ in range(count)]
    for a, b in sorted(edges):
        graph[a].append(b)
        graph[b].append(a)
    for neighbors in graph:
        rng.shuffle(neighbors)
    return {"graph": graph}


def _pair(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def validate(case_input: dict) -> None:
    graph = case_input["graph"]
    count = len(graph)
    assert 1 <= count <= MAX_NODES, "node count out of range"
    assert sum(len(neighbors) for neighbors in graph) <= 10**5, "too many edges"
    links = set()
    for node, neighbors in enumerate(graph):
        assert len(set(neighbors)) == len(neighbors), "edge listed twice"
        for neighbor in neighbors:
            assert 0 <= neighbor < count and neighbor != node, "bad neighbor"
            links.add((node, neighbor))
    assert all((b, a) in links for a, b in links), "edges are not symmetric"
