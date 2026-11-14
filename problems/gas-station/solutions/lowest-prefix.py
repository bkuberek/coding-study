def can_complete_circuit(gas: list[int], cost: list[int]) -> int:
    # balance is the fuel after driving from station 0 past `station` (it may go negative).
    # Starting right after the station where it is lowest lifts every point of the trip to
    # at least zero, provided the whole circle does not lose fuel.
    balance = 0
    lowest = 0
    start = 0
    for station in range(len(gas)):
        balance += gas[station] - cost[station]
        if balance < lowest:
            lowest = balance
            start = station + 1
    if balance < 0:
        return -1
    return start % len(gas)
