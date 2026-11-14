package kth_largest_in_stream

import "slices"

type KthLargestTracker struct {
	k      int
	values []int // every number so far, ascending
}

func NewKthLargestTracker(k int, nums []int) *KthLargestTracker {
	values := slices.Clone(nums)
	slices.Sort(values)
	return &KthLargestTracker{k: k, values: values}
}

func (t *KthLargestTracker) Add(value int) int {
	// The binary search is O(log n); shifting the tail to open the slot is O(n).
	position, _ := slices.BinarySearch(t.values, value)
	t.values = slices.Insert(t.values, position, value)
	// The kth largest is the kth entry from the end.
	return t.values[len(t.values)-t.k]
}
