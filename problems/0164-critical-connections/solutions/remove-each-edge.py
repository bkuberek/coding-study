def critical_connections(n: int, connections: list[list[int]]) -> list[list[int]]:
    adjacency: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    for index, (a, b) in enumerate(connections):
        adjacency[a].append((b, index))
        adjacency[b].append((a, index))

    def connected_without(skipped: int) -> bool:
        """Can every server still be reached from server 0 when cable `skipped` is cut?"""
        seen = [False] * n
        seen[0] = True
        stack = [0]
        reached = 1
        while stack:
            for neighbor, index in adjacency[stack.pop()]:
                if index != skipped and not seen[neighbor]:
                    seen[neighbor] = True
                    reached += 1
                    stack.append(neighbor)
        return reached == n

    return [list(cable) for index, cable in enumerate(connections) if not connected_without(index)]
