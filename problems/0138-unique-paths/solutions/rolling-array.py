MOD = 10**9 + 7


def unique_paths(m: int, n: int) -> int:
    # Transposing the grid does not change the count, so keep the row along the shorter side.
    width, height = min(m, n), max(m, n)
    # Before the update, routes[column] belongs to the row above; after it, to the current row.
    routes = [1] * width
    for _ in range(1, height):
        for column in range(1, width):
            routes[column] = (routes[column] + routes[column - 1]) % MOD
    return routes[-1]
