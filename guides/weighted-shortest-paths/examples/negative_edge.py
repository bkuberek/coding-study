"""One negative edge is enough to make Dijkstra's algorithm settle a node too early.

The edges are one-way. Relaxing every edge again and again, V - 1 times, still finds the truth."""

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


def relax_every_edge(source: str) -> dict[str, float]:
    best: dict[str, float] = {node: float("inf") for node in nodes}
    best[source] = 0
    for _ in range(len(nodes) - 1):
        for start, end, weight in edges:
            if best[start] + weight < best[end]:
                best[end] = best[start] + weight
    return best


print("Dijkstra:        ", dijkstra("a"))
print("relax every edge:", {node: int(d) for node, d in relax_every_edge("a").items()})
