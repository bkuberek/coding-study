import heapq


class MedianFinder:
    def __init__(self) -> None:
        # low: the smaller half as a max-heap (values negated, since heapq is a min-heap).
        # high: the larger half as a min-heap. low holds as many values as high, or one more.
        self.low: list[int] = []
        self.high: list[int] = []

    def add_num(self, num: int) -> None:
        # Route the number through low so that every value in low stays <= every value in high.
        heapq.heappush(self.high, -heapq.heappushpop(self.low, -num))
        if len(self.high) > len(self.low):
            heapq.heappush(self.low, -heapq.heappop(self.high))

    def find_median(self) -> float:
        if len(self.low) > len(self.high):
            return float(-self.low[0])
        return (-self.low[0] + self.high[0]) / 2
