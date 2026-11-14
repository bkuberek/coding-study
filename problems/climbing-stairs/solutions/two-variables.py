def climb_stairs(n: int) -> int:
    # Before each iteration: two_below and one_below count the ways to reach the two
    # steps just below the one being computed.
    two_below, one_below = 1, 1
    for _ in range(2, n + 1):
        two_below, one_below = one_below, one_below + two_below
    return one_below
