def all_grid_paths(n: int) -> list[str]:
    steps = 2 * (n - 1)
    paths: list[str] = []
    # Counting up from 0 reads the bits from the most significant one as the first move, with
    # 0 for D and 1 for R, so the sequences come out in lexicographic order. The extra top bit
    # keeps the leading zeros of the binary text; slicing it off leaves exactly `steps` digits.
    for pattern in range(1 << steps):
        moves = format(pattern | (1 << steps), "b")[1:].replace("0", "D").replace("1", "R")
        if moves.count("R") == n - 1:
            paths.append(moves)
    return paths
