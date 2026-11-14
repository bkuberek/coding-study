def car_pooling(trips: list[list[int]], capacity: int) -> bool:
    events = []
    for passengers, start, end in trips:
        events.append((start, passengers))
        events.append((end, -passengers))
    # Tuples sort by location, then by change: drop-offs (negative) come before pickups.
    events.sort()
    load = 0
    for _, change in events:
        load += change
        if load > capacity:
            return False
    return True
