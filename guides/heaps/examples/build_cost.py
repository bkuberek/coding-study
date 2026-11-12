"""Two ways to turn n items into a min-heap, counted in swaps: n pushes, each sifting up, or one
bottom-up heapify, sifting down from the last parent to the root."""

import random


def push_all(items: list[float]) -> int:
    heap: list[float] = []
    swaps = 0
    for item in items:
        heap.append(item)
        i = len(heap) - 1
        while i > 0 and heap[(i - 1) // 2] > heap[i]:
            heap[i], heap[(i - 1) // 2] = heap[(i - 1) // 2], heap[i]
            i = (i - 1) // 2
            swaps += 1
    return swaps


def heapify(items: list[float]) -> int:
    heap = list(items)
    n, swaps = len(heap), 0
    for i in reversed(range(n // 2)):
        while True:
            smallest = i
            for child in (2 * i + 1, 2 * i + 2):
                if child < n and heap[child] < heap[smallest]:
                    smallest = child
            if smallest == i:
                break
            heap[i], heap[smallest] = heap[smallest], heap[i]
            i = smallest
            swaps += 1
    return swaps


def total_height(n: int) -> int:
    """The sum of the heights of all nodes of a complete binary tree with n nodes."""
    total = 0
    for i in range(n):
        child = 2 * i + 1
        while child < n:  # the leftmost path down is the longest in a complete tree
            total += 1
            child = 2 * child + 1
    return total


rng = random.Random(7)
print("      n  input       swaps by n pushes (per item)  swaps by heapify (per item)")
for n in (1_000, 100_000):
    for name, items in (
        ("descending", [float(n - i) for i in range(n)]),
        ("random", [rng.random() for _ in range(n)]),
    ):
        pushes, built = push_all(items), heapify(items)
        print(f"{n:>7}  {name:<10} {pushes:>20} ({pushes / n:5.2f}) {built:>20} ({built / n:4.2f})")
    print(f"{n:>7}  the heights of all {n} nodes add up to {total_height(n)}")
