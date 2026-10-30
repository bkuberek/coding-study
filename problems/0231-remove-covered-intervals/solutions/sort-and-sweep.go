package remove_covered_intervals

import (
	"cmp"
	"slices"
)

func removeCoveredIntervals(intervals [][]int) int {
	ordered := slices.Clone(intervals)
	// Equal starts: the longer interval comes first, so it covers the shorter ones after it.
	slices.SortFunc(ordered, func(a, b []int) int {
		return cmp.Or(cmp.Compare(a[0], b[0]), cmp.Compare(b[1], a[1]))
	})
	remaining := 0
	reach := -1 // the largest end among the intervals already swept
	for _, interval := range ordered {
		if interval[1] > reach {
			remaining++
			reach = interval[1]
		}
	}
	return remaining
}
