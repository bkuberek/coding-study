import heapq


def find_maximized_capital(k: int, w: int, profits: list[int], capital: list[int]) -> int:
    projects = sorted(zip(capital, profits))  # cheapest requirement first
    affordable: list[int] = []  # negated profits: heapq is a min-heap
    unlocked = 0
    for _ in range(k):
        # Capital only grows, so every project unlocked once stays affordable.
        while unlocked < len(projects) and projects[unlocked][0] <= w:
            heapq.heappush(affordable, -projects[unlocked][1])
            unlocked += 1
        if not affordable:
            break  # nothing affordable now, and capital cannot grow any more
        w -= heapq.heappop(affordable)
    return w
