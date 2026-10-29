def employee_free_time(schedule: list[list[list[int]]]) -> list[list[int]]:
    intervals = sorted(interval for shifts in schedule for interval in shifts)
    free = []
    busy_until = intervals[0][1]
    for start, end in intervals:
        if start > busy_until:
            free.append([busy_until, start])
        busy_until = max(busy_until, end)
    return free
