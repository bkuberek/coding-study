def has_path(n: int, edges: list[list[int]], source: int, target: int) -> bool:
    reached = [False] * n
    reached[source] = True
    changed = True
    while changed and not reached[target]:
        changed = False
        for a, b in edges:
            # A connection with exactly one reached end brings the other end in.
            if reached[a] != reached[b]:
                reached[a] = reached[b] = True
                changed = True
    return reached[target]
