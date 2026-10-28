from datetime import date


def coverage_gaps(periods: list[list[date]], window_start: date, window_end: date) -> list[list[date]]:
    gaps: list[list[date]] = []
    cursor = window_start  # every day of the window before cursor is covered or already reported
    for start, end in sorted((period[0], period[1]) for period in periods):
        if cursor >= window_end:
            break
        if start > cursor:
            gaps.append([cursor, min(start, window_end)])
        cursor = max(cursor, end)
    if cursor < window_end:
        gaps.append([cursor, window_end])
    return gaps
