def largest_rectangle_area(heights: list[int]) -> int:
    best = 0
    for left in range(len(heights)):
        # The tallest rectangle spanning bars left..right is as high as the lowest of them.
        lowest = heights[left]
        for right in range(left, len(heights)):
            lowest = min(lowest, heights[right])
            best = max(best, lowest * (right - left + 1))
    return best
