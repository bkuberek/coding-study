"""Pack a bag: each item is taken whole or left behind, the weights must fit the bag, and the
total value should be as large as possible. The state is (items considered, kilograms left)."""

from itertools import combinations, product

ITEMS = [("camera", 6, 30), ("tent", 5, 20), ("stove", 5, 20), ("filter", 2, 6)]  # name, kg, value
CAPACITY = 10


def fill(items: list[tuple[str, int, int]], capacity: int) -> list[list[int]]:
    """best[i][c]: the most value from the first i items in a bag that holds c kilograms."""
    best = [[0] * (capacity + 1)]  # no items yet: nothing to gain at any capacity
    for _, weight, value in items:
        above = best[-1]  # skip the item: above[c]; take it, if it fits: value + above[c - weight]
        best.append(
            [
                max(above[c], value + above[c - weight]) if weight <= c else above[c]
                for c in range(capacity + 1)
            ]
        )
    return best


def read_back(best: list[list[int]], items: list[tuple[str, int, int]]) -> list[str]:
    """Walk up from the last cell: a value that differs from the cell above means taken."""
    taken, c = [], len(best[0]) - 1
    for i in range(len(items), 0, -1):
        if best[i][c] != best[i - 1][c]:
            name, weight, _ = items[i - 1]
            taken.append(name)
            c -= weight
    return taken[::-1]


best = fill(ITEMS, CAPACITY)
print("bag holds " + "".join(f"{c:>4}" for c in range(CAPACITY + 1)))
for i, cells in enumerate(best):
    label = "no items" if i == 0 else f"+{ITEMS[i - 1][0]}"
    print(f"{label:10}" + "".join(f"{cell:>4}" for cell in cells))
print("best bag:", read_back(best, ITEMS), "worth", best[-1][-1])


def greedy_by_density(items: list[tuple[str, int, int]], capacity: int) -> tuple[list[str], int]:
    """Take items in order of value per kilogram while they fit."""
    taken, value = [], 0
    for name, weight, worth in sorted(items, key=lambda item: item[2] / item[1], reverse=True):
        if weight <= capacity:
            taken.append(name)
            capacity -= weight
            value += worth
    return taken, value


print("greedy by value per kg:", *greedy_by_density(ITEMS, CAPACITY))

room, worth = CAPACITY, 0.0
for _name, weight, value in sorted(ITEMS, key=lambda item: item[2] / item[1], reverse=True):
    share = min(weight, room)  # with divisible items, pour in as much of the densest as fits
    worth += value * share / weight
    room -= share
print("if items could be split, greedy by value per kg gets:", worth)


def brute_force(items: list[tuple[str, int, int]], capacity: int) -> int:
    return max(
        sum(value for _, _, value in subset)
        for size in range(len(items) + 1)
        for subset in combinations(items, size)
        if sum(weight for _, weight, _ in subset) <= capacity
    )


cases = wrong = 0
for weights in product(range(1, 5), repeat=3):  # every bag of three items with small numbers
    for values in product(range(1, 7), repeat=3):
        items = [(str(k), w, v) for k, (w, v) in enumerate(zip(weights, values, strict=True))]
        for capacity in range(1, 7):
            cases += 1
            optimum = brute_force(items, capacity)
            assert fill(items, capacity)[-1][-1] == optimum
            wrong += greedy_by_density(items, capacity)[1] != optimum
print(f"small cases: the table matched brute force on all {cases}; greedy was wrong on {wrong}")
