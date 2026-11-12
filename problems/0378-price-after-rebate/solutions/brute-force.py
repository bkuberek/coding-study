def prices_after_rebate(prices: list[int]) -> list[int]:
    paid = list(prices)
    for slot in range(len(prices)):
        for later in range(slot + 1, len(prices)):
            if prices[later] <= prices[slot]:
                paid[slot] = prices[slot] - prices[later]
                break
    return paid
