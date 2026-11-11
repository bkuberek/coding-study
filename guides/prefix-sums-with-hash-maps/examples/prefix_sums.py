"""Running sums turn a question about a stretch of values into a question about two points."""

from itertools import accumulate

steps = [3, 1, 4, 1, 5, 9, 2]
prefix = [0, *accumulate(steps)]  # prefix[i] = sum of the first i values
print("prefix sums:", prefix)
print("sum of steps[2..4] =", prefix[5] - prefix[2], "| check:", sum(steps[2:5]))

# Results of games: a win is +1, a loss is -1. A stretch with as many wins as losses has a net
# change of 0, so the running balance is the same before it and after it.
games = "WWLLWWWLWW"
balances = [0, *accumulate(1 if game == "W" else -1 for game in games)]
print("balances:", balances)


def longest_even_stretch(results: str) -> tuple[int, int]:
    """(length, start) of the longest stretch with as many wins as losses."""
    first_seen = {0: 0}  # balance 0 is seen before any game: the empty prefix
    balance, best = 0, (0, 0)
    for position, result in enumerate(results, start=1):
        balance += 1 if result == "W" else -1
        if balance in first_seen:
            start = first_seen[balance]
            best = max(best, (position - start, start))
        else:
            first_seen[balance] = position
    return best


def count_even_stretches(results: str, seed: bool = True) -> int:
    """How many stretches have as many wins as losses."""
    seen = {0: 1} if seed else {}
    balance = total = 0
    for result in results:
        balance += 1 if result == "W" else -1
        total += seen.get(balance, 0)  # every earlier equal balance closes one stretch
        seen[balance] = seen.get(balance, 0) + 1
    return total


length, start = longest_even_stretch(games)
print(f"longest even stretch: {length} games, {games[start:start + length]}")
brute = sum(
    1
    for left in range(len(games))
    for right in range(left + 1, len(games) + 1)
    if games[left:right].count("W") * 2 == right - left
)
print("even stretches:", count_even_stretches(games), "| checking every pair:", brute)
print("without the seed {0: 1}:", count_even_stretches(games, seed=False), "(misses those from the start)")
