def daily_temperatures(temperatures: list[int]) -> list[int]:
    waits = [0] * len(temperatures)
    # Days still waiting for a warmer day; their readings never rise from bottom to top.
    waiting: list[int] = []
    for day, temperature in enumerate(temperatures):
        while waiting and temperatures[waiting[-1]] < temperature:
            earlier = waiting.pop()
            waits[earlier] = day - earlier
        waiting.append(day)
    return waits
