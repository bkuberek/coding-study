package single_threaded_cpu

import "slices"

func getOrder(tasks [][]int) []int {
	remaining := make([]int, len(tasks)) // unprocessed task indexes, ascending
	for i := range remaining {
		remaining[i] = i
	}
	time := 0
	order := make([]int, 0, len(tasks))
	for len(remaining) > 0 {
		// Scan every waiting task; a strict < keeps the smaller index on equal times.
		best := -1
		for position, index := range remaining {
			if tasks[index][0] <= time && (best < 0 || tasks[index][1] < tasks[remaining[best]][1]) {
				best = position
			}
		}
		if best < 0 {
			// Idle until the next arrival.
			time = tasks[remaining[0]][0]
			for _, index := range remaining {
				time = min(time, tasks[index][0])
			}
			continue
		}
		index := remaining[best]
		remaining = slices.Delete(remaining, best, best+1)
		time += tasks[index][1]
		order = append(order, index)
	}
	return order
}
