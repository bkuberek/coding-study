def max_profit(prices: list[int]) -> int:
    cheapest = prices[0]
    best = 0
    for price in prices:
        # Selling today, the best purchase is the cheapest earlier day (or today: profit 0).
        best = max(best, price - cheapest)
        cheapest = min(cheapest, price)
    return best
