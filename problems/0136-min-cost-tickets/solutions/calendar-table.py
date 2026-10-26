def mincost_tickets(days: list[int], costs: list[int]) -> int:
    last_day = days[-1]
    travel = set(days)
    # cost[d] is the cheapest way to cover every trip on calendar days 1..d.
    cost = [0] * (last_day + 1)
    for d in range(1, last_day + 1):
        if d not in travel:
            cost[d] = cost[d - 1]
            continue
        cost[d] = min(
            cost[d - 1] + costs[0],
            cost[max(0, d - 7)] + costs[1],
            cost[max(0, d - 30)] + costs[2],
        )
    return cost[last_day]
