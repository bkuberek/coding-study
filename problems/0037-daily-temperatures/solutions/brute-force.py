def daily_temperatures(temperatures: list[int]) -> list[int]:
    days = len(temperatures)
    waits = [0] * days
    for day in range(days):
        for later in range(day + 1, days):
            if temperatures[later] > temperatures[day]:
                waits[day] = later - day
                break
    return waits
