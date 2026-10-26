def solve(board: list[list[str]]) -> None:
    rows, cols = len(board), len(board[0])
    edge = rows * cols  # a virtual node that every 'O' on the edge joins
    parent = list(range(rows * cols + 1))
    rank = [0] * (rows * cols + 1)

    def find(cell: int) -> int:
        root = cell
        while parent[root] != root:
            root = parent[root]
        while parent[cell] != root:
            parent[cell], cell = root, parent[cell]
        return root

    def union(a: int, b: int) -> None:
        root_a, root_b = find(a), find(b)
        if root_a == root_b:
            return
        if rank[root_a] < rank[root_b]:
            root_a, root_b = root_b, root_a
        parent[root_b] = root_a
        if rank[root_a] == rank[root_b]:
            rank[root_a] += 1

    for r in range(rows):
        for c in range(cols):
            if board[r][c] != "O":
                continue
            cell = r * cols + c
            if r in (0, rows - 1) or c in (0, cols - 1):
                union(cell, edge)
            if c + 1 < cols and board[r][c + 1] == "O":
                union(cell, cell + 1)
            if r + 1 < rows and board[r + 1][c] == "O":
                union(cell, cell + cols)
    edge_root = find(edge)
    for r in range(rows):
        for c in range(cols):
            if board[r][c] == "O" and find(r * cols + c) != edge_root:
                board[r][c] = "X"
