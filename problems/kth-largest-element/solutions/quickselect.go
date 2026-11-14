package kth_largest_element

import (
	"math/rand/v2"
	"slices"
)

func findKthLargest(nums []int, k int) int {
	values := slices.Clone(nums)
	target := len(values) - k // the answer's index in ascending order
	low, high := 0, len(values)-1
	for {
		pivot := values[low+rand.IntN(high-low+1)]
		// Three-way partition of values[low..high]: < pivot | == pivot | > pivot.
		less, scan, greater := low, low, high
		for scan <= greater {
			switch {
			case values[scan] < pivot:
				values[less], values[scan] = values[scan], values[less]
				less++
				scan++
			case values[scan] > pivot:
				values[scan], values[greater] = values[greater], values[scan]
				greater--
			default:
				scan++
			}
		}
		switch {
		case target < less:
			high = less - 1
		case target > greater:
			low = greater + 1
		default:
			return pivot
		}
	}
}
