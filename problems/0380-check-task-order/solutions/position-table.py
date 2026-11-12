def is_valid_task_order(n: int, prerequisites: list[list[int]], order: list[int]) -> bool:
    if len(order) != n:
        return False
    # position[t]: where task t stands in the order, or -1 while it has not been seen.
    position = [-1] * n
    for place, task in enumerate(order):
        if position[task] != -1:
            return False
        position[task] = place
    return all(position[before] < position[after] for before, after in prerequisites)
