def min_eating_speed(piles: list[int], h: int) -> int:
    speed = 1
    while sum((pile + speed - 1) // speed for pile in piles) > h:
        speed += 1
    return speed
