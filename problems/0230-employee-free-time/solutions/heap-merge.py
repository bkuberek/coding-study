import heapq


def employee_free_time(schedule: list[list[list[int]]]) -> list[list[int]]:
    # One entry per employee: the start of their next interval, who they are, and its position.
    upcoming = [(shifts[0][0], person, 0) for person, shifts in enumerate(schedule)]
    heapq.heapify(upcoming)
    free = []
    busy_until = upcoming[0][0]
    while upcoming:
        start, person, position = heapq.heappop(upcoming)
        if start > busy_until:
            free.append([busy_until, start])
        busy_until = max(busy_until, schedule[person][position][1])
        if position + 1 < len(schedule[person]):
            heapq.heappush(upcoming, (schedule[person][position + 1][0], person, position + 1))
    return free
