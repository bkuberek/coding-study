package kth_largest_element

import (
	"container/heap"
	"slices"
)

// minHeap implements heap.Interface with the smallest value at index 0.
type minHeap []int

func (h minHeap) Len() int           { return len(h) }
func (h minHeap) Less(i, j int) bool { return h[i] < h[j] }
func (h minHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }

func (h *minHeap) Push(value any) {
	*h = append(*h, value.(int))
}

func (h *minHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

func findKthLargest(nums []int, k int) int {
	// The heap keeps the k largest values seen so far; its root is the smallest of them.
	largest := minHeap(slices.Clone(nums[:k]))
	heap.Init(&largest)
	for _, value := range nums[k:] {
		if value > largest[0] {
			largest[0] = value
			heap.Fix(&largest, 0)
		}
	}
	return largest[0]
}
