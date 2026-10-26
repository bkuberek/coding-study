def car_fleet(target: int, position: list[int], speed: list[int]) -> int:
    # Arrival times are distance / speed; compare them by cross-multiplying, so no division.
    distance = [target - mile for mile in position]
    fleets = 0
    for car, mile in enumerate(position):
        slowest = -1
        for other, other_mile in enumerate(position):
            if other_mile > mile and (
                slowest < 0 or distance[other] * speed[slowest] > distance[slowest] * speed[other]
            ):
                slowest = other
        # The car leads its own fleet only if it arrives strictly later than the slowest car ahead.
        if slowest < 0 or distance[car] * speed[slowest] > distance[slowest] * speed[car]:
            fleets += 1
    return fleets
