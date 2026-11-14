def is_valid_task_order(n: int, prerequisites: list[list[int]], order: list[int]) -> bool:
    if len(order) != n:
        return False
    for task in range(n):
        if order.count(task) != 1:
            return False
    for before, after in prerequisites:
        if order.index(before) >= order.index(after):
            return False
    return True
