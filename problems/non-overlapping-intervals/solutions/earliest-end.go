package non_overlapping_intervals

import (
	"cmp"
	"slices"
)

func eraseOverlapIntervals(intervals [][]int) int {
	ordered := slices.Clone(intervals)
	slices.SortStableFunc(ordered, func(a, b []int) int { return cmp.Compare(a[1], b[1]) })
	kept, lastEnd := 0, 0
	for _, interval := range ordered {
		if kept == 0 || interval[0] >= lastEnd {
			kept++
			lastEnd = interval[1]
		}
	}
	return len(intervals) - kept
}
