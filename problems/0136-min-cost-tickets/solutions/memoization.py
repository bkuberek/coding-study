from functools import cache

DURATIONS = (1, 7, 30)


def mincost_tickets(days: list[int], costs: list[int]) -> int:
    def first_uncovered(index: int, duration: int) -> int:
        # A pass bought for days[index] covers through days[index] + duration - 1.
        following = index
        while following < len(days) and days[following] < days[index] + duration:
            following += 1
        return following

    @cache
    def cheapest_from(index: int) -> int:
        # The cheapest passes covering days[index:], given that earlier trips are covered.
        if index == len(days):
            return 0
        return min(
            price + cheapest_from(first_uncovered(index, duration))
            for duration, price in zip(DURATIONS, costs)
        )

    return cheapest_from(0)
