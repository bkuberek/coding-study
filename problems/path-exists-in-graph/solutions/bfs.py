from collections import deque


def has_path(n: int, edges: list[list[int]], source: int, target: int) -> bool:
    # neighbors[node] lists every node joined to `node`; each connection works both ways.
    neighbors: list[list[int]] = [[] for _ in range(n)]
    for a, b in edges:
        neighbors[a].append(b)
        neighbors[b].append(a)
    seen = [False] * n
    seen[source] = True
    queue = deque([source])
    while queue:
        node = queue.popleft()
        if node == target:
            return True
        for neighbor in neighbors[node]:
            if not seen[neighbor]:
                seen[neighbor] = True
                queue.append(neighbor)
    return False
