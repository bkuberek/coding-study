package single_threaded_cpu

import (
	"cmp"
	"container/heap"
	"slices"
)

// waitingTask is a task that has arrived: its processing time and its index.
type waitingTask struct {
	processing, index int
}

// shortestFirst implements heap.Interface: shortest processing time first, ties to the smaller
// index.
type shortestFirst []waitingTask

func (h shortestFirst) Len() int { return len(h) }
func (h shortestFirst) Less(i, j int) bool {
	if h[i].processing != h[j].processing {
		return h[i].processing < h[j].processing
	}
	return h[i].index < h[j].index
}
func (h shortestFirst) Swap(i, j int) { h[i], h[j] = h[j], h[i] }

func (h *shortestFirst) Push(task any) {
	*h = append(*h, task.(waitingTask))
}

func (h *shortestFirst) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

func getOrder(tasks [][]int) []int {
	arrivals := make([]int, len(tasks))
	for i := range arrivals {
		arrivals[i] = i
	}
	slices.SortFunc(arrivals, func(a, b int) int { return cmp.Compare(tasks[a][0], tasks[b][0]) })
	waiting := &shortestFirst{}
	time, nextArrival := 0, 0
	order := make([]int, 0, len(tasks))
	for len(order) < len(tasks) {
		if waiting.Len() == 0 && time < tasks[arrivals[nextArrival]][0] {
			time = tasks[arrivals[nextArrival]][0] // idle until the next arrival
		}
		for nextArrival < len(tasks) && tasks[arrivals[nextArrival]][0] <= time {
			index := arrivals[nextArrival]
			heap.Push(waiting, waitingTask{tasks[index][1], index})
			nextArrival++
		}
		shortest := heap.Pop(waiting).(waitingTask)
		time += shortest.processing
		order = append(order, shortest.index)
	}
	return order
}
