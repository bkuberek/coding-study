"""Keep the k best of a stream in a min-heap of size k: the weakest of the kept is at the root,
so each newcomer is compared with it once, and only a winner costs a heap operation."""

import heapq
import random


def podium(entries: list[tuple[int, str]], k: int, trace: bool = False) -> list[tuple[int, str]]:
    kept: list[tuple[int, str]] = []  # (weight, name), a min-heap by weight
    for weight, name in entries:
        if len(kept) < k:
            heapq.heappush(kept, (weight, name))
            note = "kept: the podium is not full yet"
        elif weight > kept[0][0]:
            dropped = heapq.heapreplace(kept, (weight, name))  # pop the root, push the newcomer
            note = f"kept, {dropped[1]} ({dropped[0]} kg) drops out"
        else:
            note = f"not kept: the lightest kept weighs {kept[0][0]} kg"
        if trace:
            print(f"{name:>6} {weight:>4} kg: {note}")
    return sorted(kept, reverse=True)  # the heap holds the k best, but not in order


weigh_in = [
    (412, "Hollis"),
    (388, "Maren"),
    (455, "Juno"),
    (301, "Pell"),
    (470, "Odile"),
    (433, "Brann"),
    (402, "Esk"),
    (468, "Tamsin"),
]
top = podium(weigh_in, 3, trace=True)
print("podium:", [f"{name} {weight}" for weight, name in top])
print("same as sorting everything:", top == sorted(weigh_in, reverse=True)[:3])


def heap_operations(values: list[float], k: int) -> int:
    """The same loop on bare numbers, counting the pushes and replacements it makes."""
    kept: list[float] = []
    operations = 0
    for value in values:
        if len(kept) < k:
            heapq.heappush(kept, value)
            operations += 1
        elif value > kept[0]:
            heapq.heapreplace(kept, value)
            operations += 1
    return operations


rng = random.Random(11)
stream = [rng.random() for _ in range(1_000_000)]
print("random stream of 1,000,000, k = 10:", heap_operations(stream, 10), "heap operations")
ascending = sorted(stream[:100_000])
print("ascending stream of 100,000, k = 10:", heap_operations(ascending, 10), "heap operations")
