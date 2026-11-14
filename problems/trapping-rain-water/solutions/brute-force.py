def trap(height: list[int]) -> int:
    water = 0
    for i, bar in enumerate(height):
        # Each max scans a slice in C: still O(n) work per bar.
        level = min(max(height[: i + 1]), max(height[i:]))
        water += level - bar
    return water
