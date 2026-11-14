class NumArray:
    def __init__(self, nums: list[int]) -> None:
        self.values = list(nums)
        size = len(nums)
        # tree[i] (1-based) holds the sum of the i & -i values ending at position i - 1.
        self.tree = [0] + list(nums)
        for i in range(1, size + 1):
            parent = i + (i & -i)
            if parent <= size:
                self.tree[parent] += self.tree[i]

    def update(self, index: int, value: int) -> None:
        delta = value - self.values[index]
        self.values[index] = value
        i = index + 1
        while i < len(self.tree):
            self.tree[i] += delta
            i += i & -i

    def sum_range(self, left: int, right: int) -> int:
        return self._prefix(right + 1) - self._prefix(left)

    def _prefix(self, count: int) -> int:
        """Sum of the first count values."""
        total, i = 0, count
        while i > 0:
            total += self.tree[i]
            i -= i & -i
        return total
