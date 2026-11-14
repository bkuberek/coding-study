def min_meeting_rooms(intervals: list[list[int]]) -> int:
    starts = sorted(start for start, _ in intervals)
    ends = sorted(end for _, end in intervals)
    rooms = ended = 0
    for start in starts:
        if ends[ended] <= start:
            # Some meeting has ended by now: its room is reused.
            ended += 1
        else:
            rooms += 1
    return rooms
