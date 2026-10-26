import heapq
from collections import Counter, deque


def least_interval(tasks: list[str], cooldown: int) -> int:
    # Max-heap of remaining counts (negated for heapq) for the tasks that may run now.
    ready = [-count for count in Counter(tasks).values()]
    heapq.heapify(ready)
    # Tasks that just ran, as (time they may run again, negated remaining count). Times
    # are appended in increasing order, so the front is always the next to come back.
    cooling: deque[tuple[int, int]] = deque()
    time = 0
    while ready or cooling:
        if ready:
            remaining = heapq.heappop(ready) + 1
            if remaining:
                cooling.append((time + cooldown + 1, remaining))
            time += 1
        else:
            time = cooling[0][0]  # nothing can run: skip the idle stretch at once
        while cooling and cooling[0][0] <= time:
            heapq.heappush(ready, cooling.popleft()[1])
    return time
