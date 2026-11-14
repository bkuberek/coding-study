def find_redundant_connection(edges: list[list[int]]) -> list[int]:
    neighbors: list[list[int]] = [[] for _ in range(len(edges) + 1)]

    def connected(start: int, goal: int) -> bool:
        seen = {start}
        stack = [start]
        while stack:
            node = stack.pop()
            if node == goal:
                return True
            for neighbor in neighbors[node]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        return False

    for a, b in edges:
        # The first edge whose ends are already connected closes the only cycle.
        if connected(a, b):
            return [a, b]
        neighbors[a].append(b)
        neighbors[b].append(a)
    return []
