package kth_largest_in_stream

import "container/heap"

// intHeap implements heap.Interface as a min-heap of ints: Less says that the smaller number
// belongs nearer the root.
type intHeap []int

func (h intHeap) Len() int           { return len(h) }
func (h intHeap) Less(i, j int) bool { return h[i] < h[j] }
func (h intHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }

func (h *intHeap) Push(value any) {
	*h = append(*h, value.(int))
}

func (h *intHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

type KthLargestTracker struct {
	k int
	// top holds the k largest numbers seen so far, with the smallest of them at index 0.
	top intHeap
}

func NewKthLargestTracker(k int, nums []int) *KthLargestTracker {
	tracker := &KthLargestTracker{k: k}
	for _, value := range nums {
		tracker.offer(value)
	}
	return tracker
}

func (t *KthLargestTracker) Add(value int) int {
	t.offer(value)
	return t.top[0]
}

func (t *KthLargestTracker) offer(value int) {
	heap.Push(&t.top, value)
	if t.top.Len() > t.k {
		// k + 1 numbers are in the heap; the smallest cannot be among the k largest.
		heap.Pop(&t.top)
	}
}
