import math


def network_delay_time(times: list[list[int]], n: int, k: int) -> int:
    arrival = [math.inf] * (n + 1)
    arrival[k] = 0
    # After round i, every node whose fastest route uses at most i links has its final time;
    # a fastest route has at most n - 1 links, and a round without changes ends early.
    for _ in range(n - 1):
        changed = False
        for u, v, w in times:
            if arrival[u] + w < arrival[v]:
                arrival[v] = arrival[u] + w
                changed = True
        if not changed:
            break
    latest = max(arrival[1:])
    return -1 if latest == math.inf else int(latest)
