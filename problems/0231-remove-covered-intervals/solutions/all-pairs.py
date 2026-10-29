def remove_covered_intervals(intervals: list[list[int]]) -> int:
    remaining = 0
    for i, (start, end) in enumerate(intervals):
        covered = any(
            j != i and other_start <= start and end <= other_end
            for j, (other_start, other_end) in enumerate(intervals)
        )
        if not covered:
            remaining += 1
    return remaining
