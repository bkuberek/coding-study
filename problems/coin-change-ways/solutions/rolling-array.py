def change(amount: int, coins: list[int]) -> int:
    # After processing a prefix of the coins, ways[total] counts the combinations for `total`
    # that use only those coins.
    ways = [1] + [0] * amount
    for coin in coins:
        # Increasing totals: ways[total - coin] already allows this coin, so it can repeat.
        for total in range(coin, amount + 1):
            ways[total] += ways[total - coin]
    return ways[amount]
