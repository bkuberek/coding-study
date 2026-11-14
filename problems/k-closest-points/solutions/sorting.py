def k_closest(points: list[list[int]], k: int) -> list[list[int]]:
    # Squared distances order points exactly like distances, without square roots.
    return sorted(points, key=lambda point: point[0] ** 2 + point[1] ** 2)[:k]
