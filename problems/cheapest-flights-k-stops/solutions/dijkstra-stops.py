import heapq


def find_cheapest_price(n: int, flights: list[list[int]], src: int, dst: int, k: int) -> int:
    graph: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    for start, end, cost in flights:
        graph[start].append((end, cost))
    # fewest[c] is the fewest flights with which c was settled so far. States are popped in
    # order of price, so a later state for c is useful only if it used fewer flights.
    fewest = [k + 2] * n
    heap = [(0, src, 0)]
    while heap:
        price, city, used = heapq.heappop(heap)
        if city == dst:
            return price
        if used >= fewest[city]:
            continue
        fewest[city] = used
        if used == k + 1:
            continue  # no flights left
        for neighbor, cost in graph[city]:
            heapq.heappush(heap, (price + cost, neighbor, used + 1))
    return -1
