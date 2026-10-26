from functools import cache


def max_profit(prices: list[int]) -> int:
    @cache
    def best(day: int, holding: bool) -> int:
        # The most profit obtainable from `day` on, starting with or without a share.
        if day >= len(prices):
            return 0
        wait = best(day + 1, holding)
        if holding:
            # Selling today forces tomorrow to be a cooldown day, so resume on day + 2.
            return max(wait, prices[day] + best(day + 2, False))
        return max(wait, -prices[day] + best(day + 1, True))

    return best(0, False)
