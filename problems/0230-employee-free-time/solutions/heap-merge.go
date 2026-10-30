package employee_free_time

import "container/heap"

// upcoming is one employee's next interval: its start, who they are and its position.
type upcoming struct {
	start, person, position int
}

// upcomingHeap is a min-heap ordered by start, then employee, then position.
type upcomingHeap []upcoming

func (h upcomingHeap) Len() int { return len(h) }
func (h upcomingHeap) Less(i, j int) bool {
	if h[i].start != h[j].start {
		return h[i].start < h[j].start
	}
	if h[i].person != h[j].person {
		return h[i].person < h[j].person
	}
	return h[i].position < h[j].position
}
func (h upcomingHeap) Swap(i, j int) { h[i], h[j] = h[j], h[i] }
func (h *upcomingHeap) Push(x any)   { *h = append(*h, x.(upcoming)) }
func (h *upcomingHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

func employeeFreeTime(schedule [][][]int) [][]int {
	next := make(upcomingHeap, len(schedule))
	for person, shifts := range schedule {
		next[person] = upcoming{shifts[0][0], person, 0}
	}
	heap.Init(&next)

	free := [][]int{}
	busyUntil := next[0].start
	for next.Len() > 0 {
		current := heap.Pop(&next).(upcoming)
		if current.start > busyUntil {
			free = append(free, []int{busyUntil, current.start})
		}
		shifts := schedule[current.person]
		busyUntil = max(busyUntil, shifts[current.position][1])
		if current.position+1 < len(shifts) {
			heap.Push(&next, upcoming{shifts[current.position+1][0], current.person, current.position + 1})
		}
	}
	return free
}
