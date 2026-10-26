def change(amount: int, coins: list[int]) -> int:
    # ways[i][total] caches the combinations for `total` using coins[i:]; -1 is unknown.
    ways = [[-1] * (amount + 1) for _ in range(len(coins))]

    def count(i: int, total: int) -> int:
        if total == 0:
            return 1
        if i == len(coins):
            return 0
        if ways[i][total] < 0:
            # Either no coin of value coins[i] is used, or at least one is.
            skip = count(i + 1, total)
            use = count(i, total - coins[i]) if coins[i] <= total else 0
            ways[i][total] = skip + use
        return ways[i][total]

    return count(0, amount)
