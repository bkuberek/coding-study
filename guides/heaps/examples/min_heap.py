"""A binary min-heap in a plain list, with every swap printed: push sifts up, pop sifts down,
and heapify builds a heap from the bottom up."""

import heapq


class MinHeap:
    def __init__(self, items: list[int] | None = None, trace: bool = True) -> None:
        self.items = list(items or [])
        self.trace = trace
        self.swaps = 0

    def swap(self, i: int, j: int) -> None:
        a = self.items
        if self.trace:
            print(f"    swap {a[i]} (index {i}) with {a[j]} (index {j})")
        a[i], a[j] = a[j], a[i]
        self.swaps += 1

    def sift_up(self, i: int) -> None:
        while i > 0:
            parent = (i - 1) // 2
            if self.items[parent] <= self.items[i]:
                return  # the parent is no larger: the heap property holds again
            self.swap(i, parent)
            i = parent

    def sift_down(self, i: int) -> None:
        n = len(self.items)
        while True:
            smallest = i
            for child in (2 * i + 1, 2 * i + 2):
                if child < n and self.items[child] < self.items[smallest]:
                    smallest = child
            if smallest == i:
                return  # no child is smaller: the heap property holds again
            self.swap(i, smallest)
            i = smallest

    def push(self, item: int) -> None:
        self.items.append(item)  # the next free place keeps the tree complete
        self.sift_up(len(self.items) - 1)

    def pop(self) -> int:
        top = self.items[0]
        last = self.items.pop()
        if self.items:
            self.items[0] = last  # the last leaf fills the hole at the root
            self.sift_down(0)
        return top

    def heapify(self) -> None:
        for i in reversed(range(len(self.items) // 2)):  # every node that has a child
            self.sift_down(i)


heap = MinHeap()
for item in (31, 14, 42, 9, 26, 19):
    print(f"push {item}")
    heap.push(item)
    print(f"    heap: {heap.items}")

print("pop")
print(f"    returned {heap.pop()}, heap: {heap.items}")

data = [17, 8, 12, 5, 3, 10, 4, 1]
print(f"heapify {data}")
built = MinHeap(data)
built.heapify()
print(f"    heap: {built.items}, {built.swaps} swaps")

reference = list(data)
heapq.heapify(reference)
built.trace = False
ours = [built.pop() for _ in data]
theirs = [heapq.heappop(reference) for _ in data]
print("pops in the same order as heapq:", ours == theirs, ours)
