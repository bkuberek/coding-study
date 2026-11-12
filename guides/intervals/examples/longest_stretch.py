"""A channel airs segments [start, end) in minutes, some of them at the same time. How long is the
longest stretch during which something was on air without a break?"""

Interval = tuple[int, int]


def longest_unbroken(segments: list[Interval]) -> int:
    """Minutes of the longest stretch with no break, printing how long the current one lasts."""
    ordered = sorted(segments)
    since, reach = ordered[0]  # when the current stretch began, and how far it reaches so far
    longest = 0
    for start, end in ordered:
        if start > reach:
            since, reach = start, end
        else:
            reach = max(reach, end)  # a segment may end before the stretch does
        longest = max(longest, reach - since)
        print(f"[{start:>2}, {end:>2}): on air for {reach - since:>2} minutes without a break")
    return longest


segments = [(30, 45), (0, 10), (8, 20), (12, 15), (20, 26), (40, 52), (60, 70)]
print("longest unbroken stretch:", longest_unbroken(segments), "minutes")
