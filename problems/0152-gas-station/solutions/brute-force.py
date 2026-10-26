def can_complete_circuit(gas: list[int], cost: list[int]) -> int:
    n = len(gas)
    for start in range(n):
        fuel = 0
        for step in range(n):
            station = (start + step) % n
            fuel += gas[station] - cost[station]
            if fuel < 0:
                break
        else:
            return start
    return -1
