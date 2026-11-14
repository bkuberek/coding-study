class NumArray:
    def __init__(self, nums: list[int]) -> None:
        self.size = len(nums)
        # Leaves at size .. 2 * size - 1; node i holds the sum of its children 2i and 2i + 1.
        self.tree = [0] * self.size + list(nums)
        for node in range(self.size - 1, 0, -1):
            self.tree[node] = self.tree[2 * node] + self.tree[2 * node + 1]

    def update(self, index: int, value: int) -> None:
        node = index + self.size
        self.tree[node] = value
        while node > 1:
            node //= 2
            self.tree[node] = self.tree[2 * node] + self.tree[2 * node + 1]

    def sum_range(self, left: int, right: int) -> int:
        total = 0
        low, high = left + self.size, right + self.size + 1  # half-open [low, high)
        while low < high:
            if low & 1:
                total += self.tree[low]
                low += 1
            if high & 1:
                high -= 1
                total += self.tree[high]
            low //= 2
            high //= 2
        return total
