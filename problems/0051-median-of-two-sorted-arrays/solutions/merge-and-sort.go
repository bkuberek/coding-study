package median_of_two_sorted_arrays

import "slices"

func findMedianSortedArrays(nums1 []int, nums2 []int) float64 {
	merged := slices.Concat(nums1, nums2)
	slices.Sort(merged)
	middle := len(merged) / 2
	if len(merged)%2 == 1 {
		return float64(merged[middle])
	}
	return float64(merged[middle-1]+merged[middle]) / 2
}
