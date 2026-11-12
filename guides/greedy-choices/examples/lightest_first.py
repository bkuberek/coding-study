"""A cargo bike carries at most 20 kg. Taking the lightest parcels first carries the most parcels,
and its load after k parcels never exceeds the load of any other plan after its k lightest."""

from itertools import accumulate, combinations

CAPACITY_KG = 20


def lightest_first(parcels: list[int]) -> list[int]:
    taken: list[int] = []
    for weight in sorted(parcels):
        if sum(taken) + weight > CAPACITY_KG:
            break
        taken.append(weight)
    return taken


def most_parcels_by_brute_force(parcels: list[int]) -> int:
    return max(
        size
        for size in range(len(parcels) + 1)
        for plan in combinations(parcels, size)
        if sum(plan) <= CAPACITY_KG
    )


parcels = [9, 3, 7, 4, 6, 8]
greedy = lightest_first(parcels)
other_plan = [9, 4, 7]
print("lightest first takes", greedy, "->", len(greedy), "parcels")
print("another plan that fits:", other_plan, "->", len(other_plan), "parcels")
print("load after k parcels, greedy:  ", list(accumulate(greedy)))
print("load after k parcels, the plan:", list(accumulate(sorted(other_plan))))
print("most parcels of any plan:", most_parcels_by_brute_force(parcels))
