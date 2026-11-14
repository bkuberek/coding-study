def prices_after_rebate(prices: list[int]) -> list[int]:
    paid = list(prices)
    # Slots still waiting for a rebate; their prices rise strictly from bottom to top.
    waiting: list[int] = []
    for slot, price in enumerate(prices):
        while waiting and prices[waiting[-1]] >= price:
            earlier = waiting.pop()
            paid[earlier] = prices[earlier] - price
        waiting.append(slot)
    return paid
