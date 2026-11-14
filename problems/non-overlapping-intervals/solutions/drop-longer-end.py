def erase_overlap_intervals(intervals: list[list[int]]) -> int:
    ordered = sorted(intervals)
    removed = 0
    kept_end = ordered[0][1]
    for start, end in ordered[1:]:
        if start < kept_end:
            # Conflict: keep whichever of the two ends first.
            removed += 1
            kept_end = min(kept_end, end)
        else:
            kept_end = end
    return removed
