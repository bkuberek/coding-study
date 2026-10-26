import heapq


def find_kth_largest(nums: list[int], k: int) -> int:
    # The heap keeps the k largest values seen so far; its root is the smallest of them.
    heap = nums[:k]
    heapq.heapify(heap)
    for value in nums[k:]:
        if value > heap[0]:
            heapq.heapreplace(heap, value)
    return heap[0]
