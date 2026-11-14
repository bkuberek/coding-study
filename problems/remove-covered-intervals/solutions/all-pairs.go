package remove_covered_intervals

func removeCoveredIntervals(intervals [][]int) int {
	remaining := 0
	for i, interval := range intervals {
		covered := false
		for j, other := range intervals {
			if j != i && other[0] <= interval[0] && interval[1] <= other[1] {
				covered = true
				break
			}
		}
		if !covered {
			remaining++
		}
	}
	return remaining
}
