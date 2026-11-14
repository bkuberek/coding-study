package non_overlapping_intervals

import "slices"

func eraseOverlapIntervals(intervals [][]int) int {
	ordered := slices.Clone(intervals)
	slices.SortFunc(ordered, slices.Compare[[]int])
	// longest[i]: the most intervals that can be kept among ordered[:i + 1], ending with ordered[i].
	longest := make([]int, len(ordered))
	most := 0
	for i, interval := range ordered {
		best := 0
		for j := 0; j < i; j++ {
			if ordered[j][1] <= interval[0] {
				best = max(best, longest[j])
			}
		}
		longest[i] = best + 1
		most = max(most, longest[i])
	}
	return len(intervals) - most
}
