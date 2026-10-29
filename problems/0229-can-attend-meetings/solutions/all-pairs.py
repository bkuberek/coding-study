def can_attend_meetings(intervals: list[list[int]]) -> bool:
    for i in range(len(intervals)):
        first_start, first_end = intervals[i]
        for j in range(i + 1, len(intervals)):
            second_start, second_end = intervals[j]
            # Half-open meetings share a moment exactly when each starts before the other ends.
            if first_start < second_end and second_start < first_end:
                return False
    return True
