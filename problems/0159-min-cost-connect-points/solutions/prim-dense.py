import math


def min_cost_connect_points(points: list[list[int]]) -> int:
    n = len(points)
    # cheapest[i] is the cheapest cable from point i to the tree built so far.
    cheapest = [math.inf] * n
    in_tree = [False] * n
    cheapest[0] = 0
    total = 0
    for _ in range(n):
        point = min((i for i in range(n) if not in_tree[i]), key=cheapest.__getitem__)
        in_tree[point] = True
        total += cheapest[point]
        x, y = points[point]
        for other in range(n):
            if not in_tree[other]:
                cost = abs(x - points[other][0]) + abs(y - points[other][1])
                if cost < cheapest[other]:
                    cheapest[other] = cost
    return int(total)
