import heapq


def k_closest(points: list[list[int]], k: int) -> list[list[int]]:
    # heapq is a min-heap; negated distances put the farthest kept point at the root.
    # The index breaks ties, so the point lists themselves are never compared.
    heap: list[tuple[int, int]] = []
    for index, (x, y) in enumerate(points):
        entry = (-(x * x + y * y), index)
        if len(heap) < k:
            heapq.heappush(heap, entry)
        elif entry > heap[0]:
            heapq.heapreplace(heap, entry)
    return [points[index] for _, index in heap]
