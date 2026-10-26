def total_fruit(fruits: list[int]) -> int:
    best = 0
    for start in range(len(fruits)):
        first, second = fruits[start], None
        end = start
        while end < len(fruits):
            fruit = fruits[end]
            if fruit != first and fruit != second:
                if second is not None:
                    break
                second = fruit
            end += 1
        best = max(best, end - start)
    return best
