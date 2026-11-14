package employee_free_time

import (
	"cmp"
	"slices"
)

func employeeFreeTime(schedule [][][]int) [][]int {
	var intervals [][]int
	for _, shifts := range schedule {
		intervals = append(intervals, shifts...)
	}
	slices.SortFunc(intervals, func(a, b []int) int {
		return cmp.Or(cmp.Compare(a[0], b[0]), cmp.Compare(a[1], b[1]))
	})
	free := [][]int{}
	busyUntil := intervals[0][1]
	for _, interval := range intervals {
		if interval[0] > busyUntil {
			free = append(free, []int{busyUntil, interval[0]})
		}
		busyUntil = max(busyUntil, interval[1])
	}
	return free
}
