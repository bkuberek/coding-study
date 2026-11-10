def all_grid_paths(n: int) -> list[str]:
    last = n - 1
    paths: list[str] = []
    moves: list[str] = []

    def extend(downs: int, rights: int) -> None:
        if downs == last and rights == last:
            paths.append("".join(moves))
            return
        # D is tried before R, so the paths come out in lexicographic order.
        if downs < last:
            moves.append("D")
            extend(downs + 1, rights)
            moves.pop()
        if rights < last:
            moves.append("R")
            extend(downs, rights + 1)
            moves.pop()

    extend(0, 0)
    return paths
