"""Seeded inputs for path-exists-in-graph.

`n` is the number of nodes (at most 2000). From 100 nodes on, the sizes the ladder times, every
input has the same shape: all n nodes sit on one chain under shuffled labels, the source is one
end of it and the target the other end, and the connections are listed starting from the target
end. Sweeping a list in that order reaches one new node per pass, so the sweep needs about n
passes over n - 1 connections, while a search that builds an adjacency list and a union-find
both stay linear. The answer is always true.

Below 100 nodes, which covers the oracle's inputs, the graphs are random and sparse: up to twice
as many connections as nodes, a random source and a random target (equal now and then), so the
answer is true and false about equally often.
"""

import random

MAX_NODES = 2000
MAX_EDGES = 5000
CHAIN_FROM = 100
EDGES_PER_NODE = 2


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_NODES)
    labels = list(range(count))
    rng.shuffle(labels)
    if count >= CHAIN_FROM:
        edges = [[labels[i], labels[i + 1]] for i in range(count - 2, -1, -1)]
        return {"n": count, "edges": edges, "source": labels[0], "target": labels[-1]}
    pairs = [(a, b) for a in range(count) for b in range(a + 1, count)]
    wanted = rng.randint(0, min(len(pairs), EDGES_PER_NODE * count))
    edges = [list(pair) if rng.random() < 0.5 else [pair[1], pair[0]] for pair in rng.sample(pairs, wanted)]
    return {
        "n": count,
        "edges": edges,
        "source": rng.randrange(count),
        "target": rng.randrange(count),
    }


def validate(case_input: dict) -> None:
    count, edges = case_input["n"], case_input["edges"]
    assert 1 <= count <= MAX_NODES, "node count out of range"
    assert len(edges) <= MAX_EDGES, "too many edges"
    assert all(len(edge) == 2 for edge in edges), "edges need two endpoints"
    assert all(0 <= node < count for edge in edges for node in edge), "node out of range"
    assert all(a != b for a, b in edges), "no self-loops"
    assert len({frozenset(edge) for edge in edges}) == len(edges), "edges must be distinct"
    assert 0 <= case_input["source"] < count, "source out of range"
    assert 0 <= case_input["target"] < count, "target out of range"
