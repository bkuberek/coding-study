package task_scheduler

import "container/heap"

// maxHeap implements heap.Interface with the largest remaining count at index 0.
type maxHeap []int

func (h maxHeap) Len() int           { return len(h) }
func (h maxHeap) Less(i, j int) bool { return h[i] > h[j] }
func (h maxHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }

func (h *maxHeap) Push(count any) {
	*h = append(*h, count.(int))
}

func (h *maxHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

// cooling is a task that just ran: the time it may run again and how many copies are left.
type cooling struct {
	readyAt, remaining int
}

func leastInterval(tasks []rune, cooldown int) int {
	var counts [26]int
	for _, task := range tasks {
		counts[task-'A']++
	}
	// Max-heap of remaining counts for the tasks that may run now.
	ready := &maxHeap{}
	for _, count := range counts {
		if count > 0 {
			*ready = append(*ready, count)
		}
	}
	heap.Init(ready)
	// Times are appended in increasing order, so the front is always the next to come back.
	var waiting []cooling
	time := 0
	for ready.Len() > 0 || len(waiting) > 0 {
		if ready.Len() > 0 {
			remaining := heap.Pop(ready).(int) - 1
			if remaining > 0 {
				waiting = append(waiting, cooling{time + cooldown + 1, remaining})
			}
			time++
		} else {
			time = waiting[0].readyAt // nothing can run: skip the idle stretch at once
		}
		for len(waiting) > 0 && waiting[0].readyAt <= time {
			heap.Push(ready, waiting[0].remaining)
			waiting = waiting[1:]
		}
	}
	return time
}
