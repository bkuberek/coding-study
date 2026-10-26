import random


def k_closest(points: list[list[int]], k: int) -> list[list[int]]:
    distance = [x * x + y * y for x, y in points]
    order = list(range(len(points)))
    low, high = 0, len(order) - 1
    # Partition until position k - 1 holds its sorted entry; then positions 0..k-1 hold
    # the k closest points (in some order).
    while low < high:
        pivot = distance[order[random.randint(low, high)]]
        less, scan, greater = low, low, high
        while scan <= greater:
            value = distance[order[scan]]
            if value < pivot:
                order[less], order[scan] = order[scan], order[less]
                less += 1
                scan += 1
            elif value > pivot:
                order[scan], order[greater] = order[greater], order[scan]
                greater -= 1
            else:
                scan += 1
        if k - 1 < less:
            high = less - 1
        elif k - 1 > greater:
            low = greater + 1
        else:
            break
    return [points[index] for index in order[:k]]
