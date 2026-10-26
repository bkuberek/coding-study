import math


def find_cheapest_price(n: int, flights: list[list[int]], src: int, dst: int, k: int) -> int:
    # price[c] is the cheapest known price to reach c with at most `round` flights.
    price = [math.inf] * n
    price[src] = 0
    for _ in range(k + 1):
        # Read from the previous round only, so one round never chains two flights.
        previous = price[:]
        changed = False
        for start, end, cost in flights:
            if previous[start] + cost < price[end]:
                price[end] = previous[start] + cost
                changed = True
        if not changed:
            break
    return -1 if price[dst] == math.inf else int(price[dst])
