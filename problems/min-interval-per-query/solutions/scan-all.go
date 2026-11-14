package min_interval_per_query

func minInterval(intervals [][]int, queries []int) []int {
	answer := make([]int, len(queries))
	for i, query := range queries {
		smallest := -1
		for _, interval := range intervals {
			if interval[0] <= query && query <= interval[1] {
				size := interval[1] - interval[0] + 1
				if smallest == -1 || size < smallest {
					smallest = size
				}
			}
		}
		answer[i] = smallest
	}
	return answer
}
