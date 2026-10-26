def calc_equation(equations: list[list[str]], values: list[float], queries: list[list[str]]) -> list[float]:
    # parent[x] is x's parent; weight[x] is the value of x / parent[x].
    parent: dict[str, str] = {}
    weight: dict[str, float] = {}

    def find(name: str) -> tuple[str, float]:
        """Return (root, name / root), compressing the path on the way."""
        path = []
        while parent[name] != name:
            path.append(name)
            name = parent[name]
        root = name
        # Walk back from the node nearest the root, so each weight already points at the root.
        for node in reversed(path):
            if parent[node] != root:
                weight[node] *= weight[parent[node]]
                parent[node] = root
        return root, weight[path[0]] if path else 1.0

    for (a, b), value in zip(equations, values, strict=True):
        for name in (a, b):
            if name not in parent:
                parent[name], weight[name] = name, 1.0
        root_a, a_over_root_a = find(a)
        root_b, b_over_root_b = find(b)
        if root_a != root_b:
            # Hang root_a under root_b: root_a / root_b = (a / b) * (b / root_b) / (a / root_a).
            parent[root_a] = root_b
            weight[root_a] = value * b_over_root_b / a_over_root_a

    answers = []
    for c, d in queries:
        if c not in parent or d not in parent:
            answers.append(-1.0)
            continue
        root_c, c_over_root = find(c)
        root_d, d_over_root = find(d)
        answers.append(c_over_root / d_over_root if root_c == root_d else -1.0)
    return answers
