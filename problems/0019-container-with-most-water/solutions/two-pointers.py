def max_area(height: list[int]) -> int:
    left, right = 0, len(height) - 1
    best = 0
    while left < right:
        width = right - left
        if height[left] < height[right]:
            best = max(best, width * height[left])
            left += 1
        else:
            best = max(best, width * height[right])
            right -= 1
    return best
