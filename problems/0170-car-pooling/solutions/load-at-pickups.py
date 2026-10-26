def car_pooling(trips: list[list[int]], capacity: int) -> bool:
    # The load is highest right after some pickup, so checking every pickup point suffices.
    busiest = 0
    for _, pickup, _ in trips:
        load = sum(passengers for passengers, start, end in trips if start <= pickup < end)
        busiest = max(busiest, load)
    return busiest <= capacity
