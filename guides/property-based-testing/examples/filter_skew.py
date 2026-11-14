"""Two ways to get sorted lists for a test: filter random lists, or build sorted ones.

Filtering keeps only the random lists that happen to be sorted. It throws most draws away, and
the lists it keeps are mostly very short, because a long random list is rarely sorted. Building
a sorted list directly wastes nothing and gives every length its share.
"""

import random
from collections import Counter

rng = random.Random(7)


def random_list() -> list[int]:
    return [int(rng.random() * 10) for _ in range(int(rng.random() * 7))]  # length 0 to 6


draws = 10_000
filtered = [xs for xs in (random_list() for _ in range(draws)) if xs == sorted(xs)]
built = [sorted(random_list()) for _ in range(len(filtered))]

print(f"filtering: kept {len(filtered)} of {draws} draws, discarded {draws - len(filtered)}")
print("length   filtered   built")
by_length_filtered = Counter(len(xs) for xs in filtered)
by_length_built = Counter(len(xs) for xs in built)
for length in range(7):
    print(f"{length:>6} {by_length_filtered[length]:>10} {by_length_built[length]:>7}")
