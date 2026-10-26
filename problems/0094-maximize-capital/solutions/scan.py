def find_maximized_capital(k: int, w: int, profits: list[int], capital: list[int]) -> int:
    used = [False] * len(profits)
    for _ in range(k):
        best = -1
        for index, profit in enumerate(profits):
            if not used[index] and capital[index] <= w and (best < 0 or profit > profits[best]):
                best = index
        if best < 0:
            break  # nothing affordable now, and capital cannot grow any more
        used[best] = True
        w += profits[best]
    return w
