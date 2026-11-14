import heapq


def network_delay_time(times: list[list[int]], n: int, k: int) -> int:
    graph: list[list[tuple[int, int]]] = [[] for _ in range(n + 1)]
    for u, v, w in times:
        graph[u].append((v, w))
    arrival: dict[int, int] = {}
    heap = [(0, k)]
    while heap:
        time, node = heapq.heappop(heap)
        if node in arrival:
            continue  # an outdated entry: the node was settled earlier with a smaller time
        arrival[node] = time
        for neighbor, w in graph[node]:
            if neighbor not in arrival:
                heapq.heappush(heap, (time + w, neighbor))
    return max(arrival.values()) if len(arrival) == n else -1
