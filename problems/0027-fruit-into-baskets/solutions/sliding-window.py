def total_fruit(fruits: list[int]) -> int:
    in_window: dict[int, int] = {}
    left = 0
    best = 0
    for right, fruit in enumerate(fruits):
        in_window[fruit] = in_window.get(fruit, 0) + 1
        while len(in_window) > 2:
            leaving = fruits[left]
            in_window[leaving] -= 1
            if in_window[leaving] == 0:
                del in_window[leaving]
            left += 1
        best = max(best, right - left + 1)
    return best
