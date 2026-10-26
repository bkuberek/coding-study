def total_fruit(fruits: list[int]) -> int:
    best = 0
    window = 0
    last, before_last = -1, -1
    last_run = 0
    for fruit in fruits:
        if fruit == last or fruit == before_last:
            window += 1
        else:
            window = last_run + 1
        if fruit == last:
            last_run += 1
        else:
            before_last, last = last, fruit
            last_run = 1
        best = max(best, window)
    return best
