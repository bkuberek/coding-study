package non_overlapping_intervals

import "slices"

func eraseOverlapIntervals(intervals [][]int) int {
	ordered := slices.Clone(intervals)
	slices.SortFunc(ordered, slices.Compare[[]int])
	removed := 0
	keptEnd := ordered[0][1]
	for _, interval := range ordered[1:] {
		start, end := interval[0], interval[1]
		if start < keptEnd {
			// Conflict: keep whichever of the two ends first.
			removed++
			keptEnd = min(keptEnd, end)
		} else {
			keptEnd = end
		}
	}
	return removed
}
