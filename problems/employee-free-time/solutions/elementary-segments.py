from itertools import pairwise


def employee_free_time(schedule: list[list[list[int]]]) -> list[list[int]]:
    intervals = [interval for shifts in schedule for interval in shifts]
    points = sorted({point for interval in intervals for point in interval})
    free = []
    for left, right in pairwise(points):
        # No interval starts or ends strictly inside (left, right): it is all busy or all free.
        if not any(start <= left < end for start, end in intervals):
            free.append([left, right])
    return free
