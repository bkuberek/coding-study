package min_meeting_rooms

import (
	"container/heap"
	"slices"
)

// intHeap is a min-heap of end times, for container/heap.
type intHeap []int

func (h intHeap) Len() int           { return len(h) }
func (h intHeap) Less(i, j int) bool { return h[i] < h[j] }
func (h intHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }
func (h *intHeap) Push(x any)        { *h = append(*h, x.(int)) }
func (h *intHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

func minMeetingRooms(intervals [][]int) int {
	ordered := slices.Clone(intervals)
	slices.SortFunc(ordered, slices.Compare[[]int])
	// End times of the meetings currently holding a room; the smallest is on top.
	ends := &intHeap{}
	for _, interval := range ordered {
		start, end := interval[0], interval[1]
		if ends.Len() > 0 && (*ends)[0] <= start {
			(*ends)[0] = end
			heap.Fix(ends, 0)
		} else {
			heap.Push(ends, end)
		}
	}
	return ends.Len()
}
