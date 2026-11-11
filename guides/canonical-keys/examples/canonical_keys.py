"""Choosing a key so that the things you call equal collide on purpose."""

from collections import defaultdict
from math import gcd


def group(items, key):
    groups = defaultdict(list)
    for item in items:
        groups[key(item)].append(item)
    return dict(groups)


# 1. Undirected edges: (a, b) and (b, a) are one road. Sort the ends.
roads = [("lyon", "paris"), ("paris", "lyon"), ("lyon", "nice")]
print("distinct roads:", sorted({tuple(sorted(road)) for road in roads}))


# 2. Word shapes: "paper" and "title" repeat letters in the same places.
def shape(word: str) -> tuple[int, ...]:
    first_seen: dict[str, int] = {}
    return tuple(first_seen.setdefault(letter, len(first_seen)) for letter in word)


words = ["paper", "title", "apple", "egg", "add", "foo"]
for key, members in group(words, shape).items():
    print("shape", key, "->", members)


# 3. Fractions: 2/4 and -1/-2 are 1/2. Divide by the gcd and put the sign on the top.
def reduced(fraction: tuple[int, int]) -> tuple[int, int]:
    top, bottom = fraction
    divisor = gcd(top, bottom) * (-1 if bottom < 0 else 1)
    return top // divisor, bottom // divisor


fractions = [(1, 2), (2, 4), (2, 3), (-1, -2), (4, 6), (3, -6)]
for key, members in group(fractions, reduced).items():
    print("value", key, "->", members)

# 4. A key built by gluing strings together can make different things collide.
glued = {"ab" + "c", "a" + "bc"}
print("glued keys for ('ab', 'c') and ('a', 'bc'):", glued)
print("tuple keys keep them apart:", len({("ab", "c"), ("a", "bc")}), "keys")
