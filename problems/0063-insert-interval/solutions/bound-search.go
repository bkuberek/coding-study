package insert_interval

import (
	"slices"
	"sort"
)

func insert(intervals [][]int, newInterval []int) [][]int {
	start, end := newInterval[0], newInterval[1]
	// Separate sorted intervals have increasing starts and increasing ends.
	first := sort.Search(len(intervals), func(i int) bool { return intervals[i][1] >= start })
	after := sort.Search(len(intervals), func(i int) bool { return intervals[i][0] > end })
	if first < after {
		start = min(start, intervals[first][0])
		end = max(end, intervals[after-1][1])
	}
	return slices.Concat(intervals[:first], [][]int{{start, end}}, intervals[after:])
}
