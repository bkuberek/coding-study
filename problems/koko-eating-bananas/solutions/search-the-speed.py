def min_eating_speed(piles: list[int], h: int) -> int:
    # Hours never increase with speed: find the first speed in [1, max(piles)] that fits.
    low, high = 1, max(piles)
    while low < high:
        speed = (low + high) // 2
        if _hours_at(piles, speed) <= h:
            high = speed
        else:
            low = speed + 1
    return low


def _hours_at(piles: list[int], speed: int) -> int:
    return sum(-(-pile // speed) for pile in piles)
