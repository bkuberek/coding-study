"""Close in from both ends of a sorted list: each step settles every remaining pair of one value."""

from itertools import combinations, combinations_with_replacement


def count_pairs_within(prices: list[int], budget: int, start: int = 0, trace: bool = False) -> int:
    """How many pairs of different positions from `start` on have a sum of at most `budget`."""
    i, j, count = start, len(prices) - 1, 0
    while i < j:
        total = prices[i] + prices[j]
        if total > budget:  # prices[j] is too dear even with the cheapest partner left
            if trace:
                print(f"  i={i} j={j}: {prices[i]} + {prices[j]} = {total} > {budget}: drop {prices[j]}")
            j -= 1
        else:  # prices[i] fits with every partner from i + 1 to j
            if trace:
                print(f"  i={i} j={j}: {prices[i]} + {prices[j]} = {total} <= {budget}: count {j - i}")
            count += j - i
            i += 1
    return count


def count_triples_within(prices: list[int], budget: int) -> int:
    """Fix the smallest of the three, then count the pairs after it."""
    return sum(
        count_pairs_within(prices, budget - prices[first], start=first + 1)
        for first in range(len(prices))
    )


prices = [2, 3, 5, 8, 9, 13]
print("pairs within 12 among", prices)
pairs = count_pairs_within(prices, 12, trace=True)
every_pair = sum(1 for a, b in combinations(prices, 2) if a + b <= 12)
print("pairs:", pairs, "| checking every pair:", every_pair)

cases = disagreements = 0
for size in range(7):
    for values in combinations_with_replacement(range(6), size):  # every sorted list
        for budget in range(12):
            cases += 1
            pairs_ok = count_pairs_within(list(values), budget) == sum(
                1 for a, b in combinations(values, 2) if a + b <= budget
            )
            triples_ok = count_triples_within(list(values), budget) == sum(
                1 for a, b, c in combinations(values, 3) if a + b + c <= budget
            )
            disagreements += not (pairs_ok and triples_ok)
print(f"pairs and triples against every combination: {cases} cases, {disagreements} disagreements")

unsorted = [9, 2, 13, 5, 3, 8]
by_value = sorted((value, position) for position, value in enumerate(unsorted))
print("sorted with original positions:", by_value)
