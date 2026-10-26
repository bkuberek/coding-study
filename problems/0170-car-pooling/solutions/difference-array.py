from itertools import accumulate


def car_pooling(trips: list[list[int]], capacity: int) -> bool:
    last = max(end for _, _, end in trips)
    # change[x] is how much the load changes at location x; its prefix sums are the loads.
    change = [0] * (last + 1)
    for passengers, start, end in trips:
        change[start] += passengers
        change[end] -= passengers
    return max(accumulate(change)) <= capacity
