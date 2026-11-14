SKIP, BAD = 2, 1


def first_bad_commit(statuses: list[int]) -> list[int]:
    first_bad = _first_bad(statuses)
    last_good = _last_good_before(statuses, first_bad)
    return [last_good + 1, first_bad]


def _first_bad(statuses: list[int]) -> int:
    # Some commit is bad, so the first bad commit is somewhere in [low, high].
    low, high = 0, len(statuses) - 1
    while low < high:
        middle = (low + high) // 2
        probe = middle
        while probe >= low and statuses[probe] == SKIP:
            probe -= 1
        if probe >= low and statuses[probe] == BAD:
            high = probe
        else:
            low = middle + 1
    return low


def _last_good_before(statuses: list[int], first_bad: int) -> int:
    # Before the first bad commit every commit that was tested is good. The last good one is
    # somewhere in [low, high], where -1 stands for "none".
    low, high = -1, first_bad - 1
    while low < high:
        middle = (low + high + 1) // 2
        probe = middle
        while probe <= high and statuses[probe] == SKIP:
            probe += 1
        if probe <= high:
            low = probe
        else:
            high = middle - 1
    return low
