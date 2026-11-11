"""Count with a hash map, then find the most frequent items three ways."""

import heapq
from collections import Counter

LOG = "warn info info error info debug warn info error warn trace info".split()

counts: dict[str, int] = {}
for level in LOG:
    counts[level] = counts.get(level, 0) + 1
print("counts:", counts)
print("Counter agrees:", Counter(LOG) == counts, "| a missing key counts", Counter(LOG)["fatal"])

# 1. Sort every distinct item by count: O(d log d) for d distinct items.
by_count = sorted(counts.items(), key=lambda pair: pair[1], reverse=True)
print("sorted, top 2:", by_count[:2])

# 2. A heap keeps only the k best: O(d log k).
print("nlargest, top 2:", heapq.nlargest(2, counts.items(), key=lambda pair: pair[1]))

# 3. Buckets indexed by count: O(n), since no count exceeds n.
buckets: list[list[str]] = [[] for _ in range(len(LOG) + 1)]
for level, count in counts.items():
    buckets[count].append(level)
ranked = [level for count in range(len(LOG), 0, -1) for level in buckets[count]]
print("buckets, top 2:", ranked[:2])

# Where k cuts through a tie, "the k most frequent" has more than one right answer.
print("top 4:", Counter(LOG).most_common(4), "| debug and trace both count", counts["trace"])
