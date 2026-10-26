from collections import deque

UNCOLORED = -1


def is_bipartite(graph: list[list[int]]) -> bool:
    color = [UNCOLORED] * len(graph)
    # Every piece of the graph needs its own start node.
    for start in range(len(graph)):
        if color[start] != UNCOLORED:
            continue
        color[start] = 0
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for neighbor in graph[node]:
                if color[neighbor] == UNCOLORED:
                    color[neighbor] = 1 - color[node]
                    queue.append(neighbor)
                elif color[neighbor] == color[node]:
                    return False
    return True
