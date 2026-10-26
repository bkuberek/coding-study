import heapq


def find_the_city(n: int, edges: list[list[int]], distance_threshold: int) -> int:
    graph: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    for a, b, w in edges:
        graph[a].append((b, w))
        graph[b].append((a, w))

    def reachable(source: int) -> int:
        """Count the other cities within the threshold, stopping once distances exceed it."""
        settled: set[int] = set()
        heap = [(0, source)]
        while heap:
            distance, city = heapq.heappop(heap)
            if distance > distance_threshold:
                break
            if city in settled:
                continue
            settled.add(city)
            for neighbor, w in graph[city]:
                if neighbor not in settled and distance + w <= distance_threshold:
                    heapq.heappush(heap, (distance + w, neighbor))
        return len(settled) - 1

    best_city, best_count = -1, n + 1
    for city in range(n):
        count = reachable(city)
        # `<=` lets a later city win a tie.
        if count <= best_count:
            best_city, best_count = city, count
    return best_city
