def erase_overlap_intervals(intervals: list[list[int]]) -> int:
    ordered = sorted(intervals)
    ends = [end for _, end in ordered]
    # longest[i]: the most intervals that can be kept among ordered[:i + 1], ending with ordered[i].
    longest: list[int] = []
    for start, _ in ordered:
        earlier = len(longest)
        best = max((longest[j] for j in range(earlier) if ends[j] <= start), default=0)
        longest.append(best + 1)
    return len(intervals) - max(longest)
