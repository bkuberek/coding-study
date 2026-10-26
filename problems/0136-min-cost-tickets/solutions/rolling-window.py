WINDOW = 30


def mincost_tickets(days: list[int], costs: list[int]) -> int:
    # cost[d % WINDOW] holds the cheapest cover of days 1..d for the last 30 calendar days;
    # nothing older is ever read, because the longest pass lasts 30 days.
    cost = [0] * WINDOW
    next_trip = 0
    for d in range(1, days[-1] + 1):
        previous = cost[(d - 1) % WINDOW]
        if d != days[next_trip]:
            cost[d % WINDOW] = previous
            continue
        next_trip += 1
        week_ago = cost[(d - 7) % WINDOW] if d >= 7 else 0
        month_ago = cost[d % WINDOW] if d >= WINDOW else 0
        cost[d % WINDOW] = min(previous + costs[0], week_ago + costs[1], month_ago + costs[2])
    return cost[days[-1] % WINDOW]
