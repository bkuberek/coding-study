def car_fleet(target: int, position: list[int], speed: list[int]) -> int:
    # Fleets formed so far, from the farthest back (bottom) to the closest to the target (top);
    # their arrival times strictly decrease from bottom to top.
    fleets: list[float] = []
    for mile, pace in sorted(zip(position, speed)):
        arrival = (target - mile) / pace
        # Every fleet behind this car that would arrive no later catches up with it.
        while fleets and fleets[-1] <= arrival:
            fleets.pop()
        fleets.append(arrival)
    return len(fleets)
