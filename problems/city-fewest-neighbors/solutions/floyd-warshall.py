import math


def find_the_city(n: int, edges: list[list[int]], distance_threshold: int) -> int:
    dist = [[math.inf] * n for _ in range(n)]
    for city in range(n):
        dist[city][city] = 0
    for a, b, w in edges:
        dist[a][b] = dist[b][a] = w
    # After step m, dist[i][j] is the shortest route that only passes through cities 0..m.
    for middle in range(n):
        through = dist[middle]
        for i in range(n):
            to_middle = dist[i][middle]
            if to_middle == math.inf:
                continue
            row = dist[i]
            for j in range(n):
                if to_middle + through[j] < row[j]:
                    row[j] = to_middle + through[j]
    best_city, best_count = -1, n + 1
    for city in range(n):
        count = sum(1 for other in range(n) if other != city and dist[city][other] <= distance_threshold)
        # `<=` lets a later city win a tie.
        if count <= best_count:
            best_city, best_count = city, count
    return best_city
