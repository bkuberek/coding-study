package insert_interval

func insert(intervals [][]int, newInterval []int) [][]int {
	var result [][]int
	start, end := newInterval[0], newInterval[1]
	index, count := 0, len(intervals)
	for index < count && intervals[index][1] < start {
		result = append(result, intervals[index])
		index++
	}
	for index < count && intervals[index][0] <= end {
		start = min(start, intervals[index][0])
		end = max(end, intervals[index][1])
		index++
	}
	result = append(result, []int{start, end})
	return append(result, intervals[index:]...)
}
