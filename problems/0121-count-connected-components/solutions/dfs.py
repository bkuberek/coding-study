def count_components(n: int, edges: list[list[int]]) -> int:
    neighbors: list[list[int]] = [[] for _ in range(n)]
    for a, b in edges:
        neighbors[a].append(b)
        neighbors[b].append(a)
    seen = [False] * n
    components = 0
    for start in range(n):
        if seen[start]:
            continue
        components += 1
        seen[start] = True
        stack = [start]  # an explicit stack avoids deep recursion on long paths
        while stack:
            node = stack.pop()
            for neighbor in neighbors[node]:
                if not seen[neighbor]:
                    seen[neighbor] = True
                    stack.append(neighbor)
    return components
