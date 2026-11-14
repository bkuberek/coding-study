"""Link two lists of people the Fellegi-Sunter way: block, compare fields, add weights, decide.

For each field, m is the chance that the field agrees when the two records are the same person,
and u the chance that it agrees when they are not. Agreement adds log2(m / u) to a pair's
weight, disagreement adds log2((1 - m) / (1 - u)). A surname's u is how common the surname is,
so agreeing on a rare one counts for more. Two thresholds split the pairs into links, possible
links for a person to review, and non-links. Only pairs that share a blocking key are compared.
"""

import math
from itertools import product

clinic = [  # id, surname, first name, birth year, postcode
    ("c1", "nakamura", "aiko", 1984, "40210"), ("c2", "smith", "john", 1990, "10115"),
    ("c3", "smith", "joan", 1990, "10117"), ("c4", "okafor", "chidi", 1975, "50667"),
    ("c5", "lindqvist", "maja", 1988, "80331"),
]
registry = [
    ("r1", "nakamura", "aiko", 1984, "40211"), ("r2", "smith", "john", 1990, "10115"),
    ("r3", "smith", "jon", 1990, "20095"), ("r4", "okafor", "chidi", 1957, "50667"),
    ("r5", "lindqvist", "maja", 1988, "80331"),
]
SURNAME_SHARE = {"smith": 0.01, "nakamura": 0.0005, "okafor": 0.0002, "lindqvist": 0.0001}
FIELDS = {"first": (1, 0.90, 0.005), "year": (2, 0.95, 0.02), "postcode": (3, 0.85, 0.001)}
UPPER, LOWER = 12.0, 4.0


def weight(a: tuple, b: tuple) -> tuple[float, list[str]]:
    total, notes = 0.0, []
    m, u = 0.95, SURNAME_SHARE[a[1]]
    agree = a[1] == b[1]
    total += math.log2(m / u) if agree else math.log2((1 - m) / (1 - u))
    notes.append(f"surname {'=' if agree else '!='}")
    for name, (index, m, u) in FIELDS.items():
        agree = a[index + 1] == b[index + 1]
        total += math.log2(m / u) if agree else math.log2((1 - m) / (1 - u))
        notes.append(f"{name} {'=' if agree else '!='}")
    return total, notes


def blocking_key(record: tuple) -> tuple[str, int]:
    return record[1][0], record[3]  # first letter of the surname, birth year


for surname, share in sorted(SURNAME_SHARE.items(), key=lambda item: -item[1]):
    print(f"agreeing on {surname} adds {math.log2(0.95 / share):5.2f}")
for name, (_, m, u) in FIELDS.items():
    print(f"{name}: agreeing adds {math.log2(m / u):5.2f}, disagreeing adds"
          f" {math.log2((1 - m) / (1 - u)):5.2f}")

pairs = [(a, b) for a, b in product(clinic, registry) if blocking_key(a) == blocking_key(b)]
print(f"pairs compared: {len(pairs)} of {len(clinic) * len(registry)}")
for a, b in pairs:
    total, notes = weight(a, b)
    decision = "link" if total >= UPPER else "possible" if total > LOWER else "non-link"
    print(f"{a[0]}-{b[0]}: {total:6.2f}  {decision:8}  {', '.join(notes)}")
missed = [(a[0], b[0]) for a, b in product(clinic, registry)
          if a[1:3] == b[1:3] and blocking_key(a) != blocking_key(b)]
print("same name, never compared:", missed)
