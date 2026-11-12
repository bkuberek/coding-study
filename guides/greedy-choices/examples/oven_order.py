"""One oven bakes one batch at a time, and every customer waits from opening until their batch
comes out. Which order of batches makes the total waiting smallest?"""

from fractions import Fraction
from itertools import permutations
from typing import NamedTuple


class Batch(NamedTuple):
    name: str
    minutes: int
    customers: int = 1


def total_wait(order: list[Batch]) -> int:
    clock = total = 0
    for batch in order:
        clock += batch.minutes
        total += clock * batch.customers
    return total


def best_of_every_order(batches: list[Batch]) -> int:
    return min(total_wait(list(order)) for order in permutations(batches))


def shortest_first(batches: list[Batch]) -> list[Batch]:
    return sorted(batches, key=lambda batch: batch.minutes)


def fewest_minutes_per_customer(batches: list[Batch]) -> list[Batch]:
    return sorted(batches, key=lambda batch: Fraction(batch.minutes, batch.customers))


def names(order: list[Batch]) -> str:
    return ", ".join(batch.name for batch in order)


batches = [Batch("bread", 5), Batch("bagels", 2), Batch("pie", 4), Batch("muffins", 1)]
print(f"as listed ({names(batches)}): total wait {total_wait(batches)}")
clock = 0
for batch in shortest_first(batches):
    clock += batch.minutes
    print(f"  {batch.name:<8} out at minute {clock:>2}")
print("shortest first: total wait", total_wait(shortest_first(batches)))
print("best of all 24 orders:", best_of_every_order(batches))
swapped = [batches[1], batches[0], *batches[2:]]
print(f"swap bread and bagels: {total_wait(batches)} -> {total_wait(swapped)}")

print()
batches = [Batch("cookies", 4, 1), Batch("croissants", 6, 3), Batch("scones", 2, 2)]
for rule in (shortest_first, fewest_minutes_per_customer):
    order = rule(batches)
    print(f"{rule.__name__} ({names(order)}): total wait {total_wait(order)}")
print("best of all 6 orders:", best_of_every_order(batches))
