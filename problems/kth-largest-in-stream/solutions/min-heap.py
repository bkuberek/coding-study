import heapq


class KthLargestTracker:
    def __init__(self, k: int, nums: list[int]) -> None:
        self.k = k
        # The k largest numbers seen so far. heapq keeps the smallest of them at index 0.
        self.top: list[int] = []
        for value in nums:
            self._offer(value)

    def add(self, value: int) -> int:
        self._offer(value)
        return self.top[0]

    def _offer(self, value: int) -> None:
        if len(self.top) < self.k:
            heapq.heappush(self.top, value)
        elif value > self.top[0]:
            # Only a number larger than the current kth largest can join the top k; it pushes
            # the old kth largest out. heapreplace pops the smallest and pushes in one step.
            heapq.heapreplace(self.top, value)
