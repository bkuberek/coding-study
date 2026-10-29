package kth_largest_element

import "slices"

func findKthLargest(nums []int, k int) int {
	sorted := slices.Clone(nums)
	slices.Sort(sorted)
	return sorted[len(sorted)-k]
}
