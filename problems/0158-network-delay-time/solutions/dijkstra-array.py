import math


def network_delay_time(times: list[list[int]], n: int, k: int) -> int:
    graph: list[list[tuple[int, int]]] = [[] for _ in range(n + 1)]
    for u, v, w in times:
        graph[u].append((v, w))
    arrival = [math.inf] * (n + 1)
    arrival[k] = 0
    settled = [False] * (n + 1)
    latest = 0
    for _ in range(n):
        # Scan for the unsettled node with the earliest arrival: O(n) per round, no heap.
        node = min((v for v in range(1, n + 1) if not settled[v]), key=arrival.__getitem__)
        if arrival[node] == math.inf:
            return -1
        settled[node] = True
        latest = arrival[node]
        for neighbor, w in graph[node]:
            if arrival[node] + w < arrival[neighbor]:
                arrival[neighbor] = arrival[node] + w
    return int(latest)
