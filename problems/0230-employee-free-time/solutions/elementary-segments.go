package employee_free_time

import "slices"

func employeeFreeTime(schedule [][][]int) [][]int {
	var intervals [][]int
	for _, shifts := range schedule {
		intervals = append(intervals, shifts...)
	}
	var points []int
	for _, interval := range intervals {
		points = append(points, interval[0], interval[1])
	}
	slices.Sort(points)
	points = slices.Compact(points)

	free := [][]int{}
	for i := 1; i < len(points); i++ {
		left, right := points[i-1], points[i]
		// No interval starts or ends strictly inside (left, right): it is all busy or all free.
		busy := slices.ContainsFunc(intervals, func(interval []int) bool {
			return interval[0] <= left && left < interval[1]
		})
		if !busy {
			free = append(free, []int{left, right})
		}
	}
	return free
}
