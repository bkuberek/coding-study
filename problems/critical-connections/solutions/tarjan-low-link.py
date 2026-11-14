def critical_connections(n: int, connections: list[list[int]]) -> list[list[int]]:
    adjacency: list[list[int]] = [[] for _ in range(n)]
    for a, b in connections:
        adjacency[a].append(b)
        adjacency[b].append(a)
    # discovered[v] is the order in which v was first reached (-1: not yet).
    # low[v] is the earliest discovery time reachable from v's subtree using at most one
    # cable that is not a tree edge.
    discovered = [-1] * n
    low = [0] * n
    bridges: list[list[int]] = []
    clock = 0

    def visit(server: int, parent: int) -> None:
        nonlocal clock
        discovered[server] = low[server] = clock
        clock += 1
        for neighbor in adjacency[server]:
            if neighbor == parent:
                continue  # the tree edge we arrived by is not a way back
            if discovered[neighbor] == -1:
                visit(neighbor, server)
                low[server] = min(low[server], low[neighbor])
                if low[neighbor] > discovered[server]:
                    bridges.append([server, neighbor])
            else:
                low[server] = min(low[server], discovered[neighbor])

    visit(0, -1)
    return bridges
