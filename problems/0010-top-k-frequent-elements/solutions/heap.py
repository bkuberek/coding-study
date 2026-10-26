import heapq
from collections import Counter


def top_k_frequent(nums: list[int], k: int) -> list[int]:
    counts = Counter(nums)
    # A min-heap of (count, value): the root is the weakest of the k entries kept so far.
    heap: list[tuple[int, int]] = []
    for value, count in counts.items():
        if len(heap) < k:
            heapq.heappush(heap, (count, value))
        elif count > heap[0][0]:
            heapq.heapreplace(heap, (count, value))
    return [value for _, value in heap]
