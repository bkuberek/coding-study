package merge_intervals

import "slices"

func merge(intervals [][]int) [][]int {
	// Sorting a copy of the outer slice leaves the caller's order alone; slices.Compare orders
	// the intervals by start, then end.
	ordered := slices.Clone(intervals)
	slices.SortFunc(ordered, slices.Compare[[]int])
	var merged [][]int
	for _, interval := range ordered {
		start, end := interval[0], interval[1]
		if last := len(merged) - 1; last >= 0 && start <= merged[last][1] {
			merged[last][1] = max(merged[last][1], end)
		} else {
			merged = append(merged, []int{start, end})
		}
	}
	return merged
}
