"""Majorities of a cluster: how many servers make one, how many can fail, and why two always meet.

A majority is more than half of all the servers. Any two majorities of the same cluster share a
server, which is checked here by trying every pair for five servers; two groups of two can miss
each other.
"""

from itertools import combinations

print("servers  majority  failures it survives")
for n in range(1, 8):
    majority = n // 2 + 1
    print(f"{n:>7}  {majority:>8}  {n - majority:>20}")

servers = range(5)
for size in (3, 2):
    pairs = list(combinations(combinations(servers, size), 2))
    apart = sum(1 for a, b in pairs if not set(a) & set(b))
    print(f"groups of {size} out of 5: {apart} of {len(pairs)} pairs share no server")
