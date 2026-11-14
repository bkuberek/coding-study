def trap(height: list[int]) -> int:
    water = 0
    falling: list[int] = []
    for right, bar in enumerate(height):
        while falling and height[falling[-1]] < bar:
            bottom = height[falling.pop()]
            if not falling:
                break
            left = falling[-1]
            level = min(height[left], bar)
            water += (right - left - 1) * (level - bottom)
        falling.append(right)
    return water
