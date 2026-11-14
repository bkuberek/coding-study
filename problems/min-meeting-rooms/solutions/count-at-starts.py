def min_meeting_rooms(intervals: list[list[int]]) -> int:
    # The busiest moment is always the start of some meeting.
    return max(
        sum(1 for start, end in intervals if start <= moment < end) for moment, _ in intervals
    )
