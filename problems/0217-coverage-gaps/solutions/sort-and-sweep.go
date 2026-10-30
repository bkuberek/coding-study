package coverage_gaps

import (
	"slices"
	"time"
)

func coverageGaps(periods [][]time.Time, windowStart time.Time, windowEnd time.Time) [][]time.Time {
	sorted := slices.Clone(periods)
	slices.SortFunc(sorted, func(a, b []time.Time) int {
		return a[0].Compare(b[0])
	})
	gaps := [][]time.Time{}
	cursor := windowStart // every day of the window before cursor is covered or already reported
	for _, period := range sorted {
		if !cursor.Before(windowEnd) {
			break
		}
		if period[0].After(cursor) {
			gapEnd := windowEnd
			if period[0].Before(windowEnd) {
				gapEnd = period[0]
			}
			gaps = append(gaps, []time.Time{cursor, gapEnd})
		}
		if period[1].After(cursor) {
			cursor = period[1]
		}
	}
	if cursor.Before(windowEnd) {
		gaps = append(gaps, []time.Time{cursor, windowEnd})
	}
	return gaps
}
