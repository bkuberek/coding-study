def max_profit(prices: list[int]) -> int:
    # A trade from day i to day j earns the sum of the daily changes between them, so the
    # answer is the best sum of a run of consecutive changes (Kadane), or 0.
    best = ending_here = 0
    for day in range(1, len(prices)):
        ending_here = max(0, ending_here + prices[day] - prices[day - 1])
        best = max(best, ending_here)
    return best
