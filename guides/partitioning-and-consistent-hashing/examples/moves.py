"""How many of 1,000 keys change node when a fifth node joins four.

Positions come from the first four bytes of a SHA-256 digest, so they run from 0 to 2^32 - 1.
Modulo placement picks node number `position mod N`. On the ring, each node puts one or more
points, and a key belongs to the point it reaches first going clockwise: the point with the
smallest clockwise distance `(point - key) mod 2^32`, which is 0 for a point exactly at the key.
"""

import hashlib

RING = 2**32
KEYS = [f"order-{i}" for i in range(1, 1001)]


def position(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:4], "big")


def modulo_owners(nodes: list[str]) -> dict[str, str]:
    return {key: nodes[position(key) % len(nodes)] for key in KEYS}


def ring_owners(nodes: list[str], points: int) -> dict[str, str]:
    ring = [(position(f"{node}/{i}"), node) for node in nodes for i in range(points)]
    owners = {}
    for key in KEYS:
        spot = position(key)
        owners[key] = min(ring, key=lambda point: (point[0] - spot) % RING)[1]
    return owners


def report(name: str, before: dict[str, str], after: dict[str, str]) -> None:
    moved = [key for key in KEYS if before[key] != after[key]]
    targets = " ".join(sorted({after[key] for key in moved}))
    loads = sorted(list(after.values()).count(node) for node in set(after.values()))
    print(f"{name:<16} {len(moved):>3} keys move, to {targets}; keys per node {loads}")


four = ["A", "B", "C", "D"]
five = [*four, "E"]
report("modulo", modulo_owners(four), modulo_owners(five))
report("ring, 1 point", ring_owners(four, 1), ring_owners(five, 1))
report("ring, 64 points", ring_owners(four, 64), ring_owners(five, 64))
