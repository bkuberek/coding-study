import bisect


class KthLargestTracker:
    def __init__(self, k: int, nums: list[int]) -> None:
        self.k = k
        self.values = sorted(nums)  # every number so far, ascending

    def add(self, value: int) -> int:
        # The binary search is O(log n); shifting the tail to open the slot is O(n).
        bisect.insort(self.values, value)
        # The kth largest is the kth entry from the end.
        return self.values[-self.k]
