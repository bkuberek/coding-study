"""Plan a week of lunch specials: one cuisine a day, never the same cuisine two days running, at the
lowest total cost. A table with one row per day and one column per cuisine."""

from itertools import pairwise, product

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
CUISINES = ["Thai", "Greek", "Mexican"]
PRICES = [  # PRICES[day][cuisine]: what serving that cuisine costs on that day
    [5, 6, 9],
    [2, 8, 9],
    [7, 4, 6],
    [6, 3, 8],
    [4, 7, 5],
]


def fill(prices: list[list[int]]) -> list[list[int]]:
    """best[d][c]: the cheapest plan for days 0..d that serves cuisine c on day d."""
    best = [prices[0][:]]  # day 0: nothing before it, so the plan costs that day's price
    for day in range(1, len(prices)):  # row by row: each row reads only the row above
        above = best[day - 1]
        best.append(
            [
                prices[day][c] + min(above[other] for other in range(len(above)) if other != c)
                for c in range(len(above))
            ]
        )
    return best


def read_back(best: list[list[int]], prices: list[list[int]]) -> list[int]:
    """Walk from the cheapest cell of the last row up to the first, one cell per day."""
    cuisine = min(range(len(best[-1])), key=lambda c: best[-1][c])
    plan = [cuisine]
    for day in range(len(best) - 1, 0, -1):
        rest = best[day][cuisine] - prices[day][cuisine]  # what days 0..day-1 must have cost
        above = best[day - 1]
        cuisine = next(c for c in range(len(above)) if c != cuisine and above[c] == rest)
        plan.append(cuisine)
    return plan[::-1]


best = fill(PRICES)
print("best[d][c]" + "".join(f"{name:>9}" for name in CUISINES))
for day, cells in zip(DAYS, best, strict=True):
    print(f"{day:10}" + "".join(f"{cell:>9}" for cell in cells))

plan = read_back(best, PRICES)
print("cheapest week:", ", ".join(CUISINES[c] for c in plan), "=", min(best[-1]))

greedy, yesterday = [], None
for day in PRICES:  # the cheapest cuisine today that differs from yesterday's
    yesterday = min((c for c in range(len(day)) if c != yesterday), key=lambda c: day[c])
    greedy.append(yesterday)
greedy_cost = sum(PRICES[day][c] for day, c in enumerate(greedy))
print("cheapest each day:", ", ".join(CUISINES[c] for c in greedy), "=", greedy_cost)

every_plan = (
    sum(PRICES[day][c] for day, c in enumerate(candidate))
    for candidate in product(range(len(CUISINES)), repeat=len(DAYS))
    if all(a != b for a, b in pairwise(candidate))
)
print("checking all 3^5 plans:", min(every_plan))


def cheapest_cost_two_rows(prices: list[list[int]]) -> int:
    """The same total keeping only the previous row; the plan itself can no longer be read back."""
    above = prices[0][:]
    for day in prices[1:]:
        above = [
            day[c] + min(above[other] for other in range(len(above)) if other != c)
            for c in range(len(above))
        ]
    return min(above)


print("two rows only:", cheapest_cost_two_rows(PRICES))
