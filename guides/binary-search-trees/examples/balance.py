"""The same keys, inserted in a different order, make search trees of very different heights.

Each insert walks down from the root and attaches the new key below the last key it compared,
so the number of keys it compared is the new key's depth. Depths never change afterwards (there
are no deletes here), so the deepest insert gives the height, and a later search for a key
compares its depth plus one keys."""

import math
import random


def build(keys: list[int]) -> tuple[int, float]:
    """Insert the keys into an empty tree; return (height, average comparisons)."""
    left: dict[int, int] = {}
    right: dict[int, int] = {}
    root = keys[0]
    height, total = 0, 1
    for key in keys[1:]:
        node, depth = root, 0
        while True:  # a loop, not recursion: the sorted case is 999 levels deep
            depth += 1
            side = left if key < node else right
            if node not in side:
                side[node] = key
                break
            node = side[node]
        height = max(height, depth)
        total += depth + 1
    return height, total / len(keys)


def shuffled(n: int, seed: int) -> list[int]:
    """A Fisher-Yates shuffle on random(), whose sequence for a seed Python keeps stable."""
    keys = list(range(n))
    rng = random.Random(seed)
    for i in range(n - 1, 0, -1):
        j = int(rng.random() * (i + 1))
        keys[i], keys[j] = keys[j], keys[i]
    return keys


for n in (1_000, 100_000):
    print(f"{n} keys, the shortest possible height: {math.floor(math.log2(n))}")
    for name, keys in (("sorted", list(range(n))), ("shuffled", shuffled(n, seed=2026))):
        if name == "sorted" and n > 1_000:
            continue  # 100,000 sorted inserts would compare about 5 * 10**9 keys
        height, average = build(keys)
        print(f"  {name:>8} order: height {height:>3}, {average:6.1f} comparisons per search")
