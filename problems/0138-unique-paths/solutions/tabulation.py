MOD = 10**9 + 7


def unique_paths(m: int, n: int) -> int:
    # routes[row][column] is the number of routes from the start to that cell. The first row
    # and the first column can only be reached in a straight line.
    routes = [[1] * n for _ in range(m)]
    for row in range(1, m):
        for column in range(1, n):
            routes[row][column] = (routes[row - 1][column] + routes[row][column - 1]) % MOD
    return routes[m - 1][n - 1]
