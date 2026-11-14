from itertools import pairwise


def can_attend_meetings(intervals: list[list[int]]) -> bool:
    ordered = sorted(intervals)
    # After sorting by start, only neighbors can be the first clash.
    return all(earlier[1] <= later[0] for earlier, later in pairwise(ordered))
