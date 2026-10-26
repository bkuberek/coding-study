def can_complete_circuit(gas: list[int], cost: list[int]) -> int:
    total = 0  # fuel balance of the whole circle
    fuel = 0  # fuel since the current candidate start
    start = 0
    for station in range(len(gas)):
        surplus = gas[station] - cost[station]
        total += surplus
        fuel += surplus
        if fuel < 0:
            # No station from `start` to `station` can be the answer; try the next one.
            start = station + 1
            fuel = 0
    return start if total >= 0 else -1
