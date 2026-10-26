def change(amount: int, coins: list[int]) -> int:
    # ways[i][total] is the number of combinations for `total` using only coins[:i].
    ways = [[0] * (amount + 1) for _ in range(len(coins) + 1)]
    ways[0][0] = 1
    for i, coin in enumerate(coins, start=1):
        for total in range(amount + 1):
            # Combinations without this coin, plus those that use it at least once.
            ways[i][total] = ways[i - 1][total]
            if total >= coin:
                ways[i][total] += ways[i][total - coin]
    return ways[len(coins)][amount]
