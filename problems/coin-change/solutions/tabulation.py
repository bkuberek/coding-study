def coin_change(coins: list[int], amount: int) -> int:
    # fewest[x] is the fewest coins that pay x exactly; amount + 1 means "cannot be paid",
    # since any real answer uses at most `amount` coins.
    unreachable = amount + 1
    fewest = [0] + [unreachable] * amount
    for x in range(1, amount + 1):
        for coin in coins:
            if coin <= x and fewest[x - coin] + 1 < fewest[x]:
                fewest[x] = fewest[x - coin] + 1
    return -1 if fewest[amount] == unreachable else fewest[amount]
