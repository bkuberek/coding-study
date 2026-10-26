from collections import defaultdict, deque


def calc_equation(equations: list[list[str]], values: list[float], queries: list[list[str]]) -> list[float]:
    # graph[a][b] is the value of a / b, stored in both directions.
    graph: dict[str, dict[str, float]] = defaultdict(dict)
    for (a, b), value in zip(equations, values, strict=True):
        graph[a][b] = value
        graph[b][a] = 1.0 / value

    def ratio(source: str, target: str) -> float:
        if source not in graph or target not in graph:
            return -1.0
        # product[x] is the value of source / x along the path that reached x.
        product = {source: 1.0}
        queue = deque([source])
        while queue:
            node = queue.popleft()
            if node == target:
                return product[node]
            for neighbor, value in graph[node].items():
                if neighbor not in product:
                    product[neighbor] = product[node] * value
                    queue.append(neighbor)
        return -1.0

    return [ratio(c, d) for c, d in queries]
