import bisect


class MedianFinder:
    def __init__(self) -> None:
        self.values: list[int] = []  # every number so far, ascending

    def add_num(self, num: int) -> None:
        # The binary search is O(log n); shifting the tail to open the slot is O(n).
        bisect.insort(self.values, num)

    def find_median(self) -> float:
        values, middle = self.values, len(self.values) // 2
        if len(values) % 2:
            return float(values[middle])
        return (values[middle - 1] + values[middle]) / 2
