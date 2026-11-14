import heapq


def max_sliding_window(nums: list[int], k: int) -> list[int]:
    heap: list[tuple[int, int]] = []
    maxima = []
    for right, value in enumerate(nums):
        heapq.heappush(heap, (-value, right))
        if right >= k - 1:
            while heap[0][1] <= right - k:
                heapq.heappop(heap)
            maxima.append(-heap[0][0])
    return maxima
