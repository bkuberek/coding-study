def coin_change(coins: list[int], amount: int) -> int:
    # Remainders are nodes; paying one coin is an edge. The first level that reaches 0 is
    # the fewest number of coins.
    seen = [False] * (amount + 1)
    seen[amount] = True
    level = [amount]
    coins_used = 0
    while level:
        if seen[0]:
            return coins_used
        next_level = []
        for remaining in level:
            for coin in coins:
                rest = remaining - coin
                if rest >= 0 and not seen[rest]:
                    seen[rest] = True
                    next_level.append(rest)
        level = next_level
        coins_used += 1
    return -1
