import heapq


def last_stone_weight(stones: list[int]) -> int:
    # heapq is a min-heap, so store negated weights: the smallest key is the heaviest stone.
    heap = [-weight for weight in stones]
    heapq.heapify(heap)
    while len(heap) > 1:
        heaviest = -heapq.heappop(heap)
        second = -heapq.heappop(heap)
        if heaviest != second:
            heapq.heappush(heap, second - heaviest)
    return -heap[0] if heap else 0
