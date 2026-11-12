"""A recursive search fails on a long path in Python; one that keeps its own stack does not.

The graph is a single path of 5,000 nodes: 0 -> 1 -> 2 -> ... -> 4999."""

import sys

NODES = 5_000
successor = {node: [node + 1] for node in range(NODES - 1)}
successor[NODES - 1] = []


def reach_recursively(node: int, seen: set[int]) -> None:
    seen.add(node)
    for nxt in successor[node]:
        if nxt not in seen:
            reach_recursively(nxt, seen)


def reach_with_a_stack(start: int) -> set[int]:
    seen = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for nxt in successor[node]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


print("recursion limit:", sys.getrecursionlimit())
try:
    reached: set[int] = set()
    reach_recursively(0, reached)
    print("recursion reached", len(reached), "nodes")
except RecursionError:
    print("recursion: RecursionError after", len(reached), "nodes")
print("own stack reached", len(reach_with_a_stack(0)), "nodes")
