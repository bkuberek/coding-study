def max_area(height: list[int]) -> int:
    best = 0
    for left in range(len(height) - 1):
        left_height = height[left]
        for right in range(left + 1, len(height)):
            right_height = height[right]
            water = (right - left) * (left_height if left_height < right_height else right_height)
            if water > best:
                best = water
    return best
