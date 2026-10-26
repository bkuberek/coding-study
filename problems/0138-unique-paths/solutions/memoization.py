MOD = 10**9 + 7


def unique_paths(m: int, n: int) -> int:
    # routes[row][column] caches the number of routes from that cell to the goal; -1 is unknown.
    routes = [[-1] * n for _ in range(m)]

    def count(row: int, column: int) -> int:
        if row == m - 1 or column == n - 1:
            return 1
        if routes[row][column] < 0:
            routes[row][column] = (count(row + 1, column) + count(row, column + 1)) % MOD
        return routes[row][column]

    return count(0, 0)
