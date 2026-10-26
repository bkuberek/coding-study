def get_order(tasks: list[list[int]]) -> list[int]:
    remaining = list(range(len(tasks)))  # unprocessed task indexes, ascending
    time = 0
    order: list[int] = []
    while remaining:
        # Scan every waiting task; a strict < keeps the smaller index on equal times.
        best = -1
        for position, index in enumerate(remaining):
            if tasks[index][0] <= time and (best < 0 or tasks[index][1] < tasks[remaining[best]][1]):
                best = position
        if best < 0:
            time = min(tasks[index][0] for index in remaining)  # idle until the next arrival
            continue
        index = remaining.pop(best)
        time += tasks[index][1]
        order.append(index)
    return order
