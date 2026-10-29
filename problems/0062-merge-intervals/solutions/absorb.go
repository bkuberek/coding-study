package merge_intervals

func merge(intervals [][]int) [][]int {
	var merged [][]int
	for _, interval := range intervals {
		start, end := interval[0], interval[1]
		// Fold every merged interval that shares a point with [start, end] into it.
		var separate [][]int
		for _, other := range merged {
			if other[0] <= end && start <= other[1] {
				start, end = min(start, other[0]), max(end, other[1])
			} else {
				separate = append(separate, other)
			}
		}
		merged = append(separate, []int{start, end})
	}
	return merged
}
