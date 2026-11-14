package insert_interval

import "slices"

func insert(intervals [][]int, newInterval []int) [][]int {
	// A fresh slice, so appending never writes into the caller's backing array.
	all := make([][]int, 0, len(intervals)+1)
	all = append(all, intervals...)
	all = append(all, newInterval)
	slices.SortFunc(all, slices.Compare[[]int])
	var merged [][]int
	for _, interval := range all {
		start, end := interval[0], interval[1]
		if last := len(merged) - 1; last >= 0 && start <= merged[last][1] {
			merged[last][1] = max(merged[last][1], end)
		} else {
			merged = append(merged, []int{start, end})
		}
	}
	return merged
}
