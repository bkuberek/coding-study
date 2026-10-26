def max_profit(prices: list[int]) -> int:
    n = len(prices)
    # Best profit at the end of day i when:
    #   hold[i]: a share is held; sold[i]: a share was sold on day i;
    #   rest[i]: no share is held and none was sold on day i (free to buy tomorrow).
    hold = [0] * n
    sold = [0] * n
    rest = [0] * n
    hold[0] = -prices[0]
    for i in range(1, n):
        hold[i] = max(hold[i - 1], rest[i - 1] - prices[i])
        sold[i] = hold[i - 1] + prices[i]
        rest[i] = max(rest[i - 1], sold[i - 1])
    return max(sold[n - 1], rest[n - 1])
