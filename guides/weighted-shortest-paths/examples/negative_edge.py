"""One negative edge is enough to make Dijkstra's algorithm settle a node too early.

The edges are one-way. The graph is small enough to try every route, which gives the truth."""

import heapq

nodes = ["a", "b", "c", "d"]
edges = [("a", "b", 2), ("a", "c", 5), ("c", "b", -4), ("b", "d", 1)]
out: dict[str, list[tuple[str, int]]] = {node: [] for node in nodes}
for start, end, weight in edges:
    out[start].append((end, weight))


def dijkstra(source: str) -> dict[str, int]:
    best = {source: 0}
    settled: set[str] = set()
    heap = [(0, source)]
    while heap:
        distance, node = heapq.heappop(heap)
        if node in settled:
            continue
        settled.add(node)
        for nxt, weight in out[node]:
            if nxt not in settled and distance + weight < best.get(nxt, float("inf")):
                best[nxt] = distance + weight
                heapq.heappush(heap, (best[nxt], nxt))
    return best


def every_route(source: str) -> dict[str, int]:
    cheapest = {source: 0}
    stack = [(source, 0)]
    while stack:  # the graph has no cycle, so every route ends
        node, cost = stack.pop()
        for nxt, weight in out[node]:
            cheapest[nxt] = min(cheapest.get(nxt, cost + weight), cost + weight)
            stack.append((nxt, cost + weight))
    return dict(sorted(cheapest.items()))


print("Dijkstra:   ", dijkstra("a"))
print("every route:", every_route("a"))
