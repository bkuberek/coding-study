package median_of_two_sorted_arrays

func findMedianSortedArrays(nums1 []int, nums2 []int) float64 {
	total := len(nums1) + len(nums2)
	i, j := 0, 0
	previous, current := 0, 0
	// Advance through the merged order until current is the value at position total / 2.
	for range total/2 + 1 {
		previous = current
		if j == len(nums2) || (i < len(nums1) && nums1[i] <= nums2[j]) {
			current = nums1[i]
			i++
		} else {
			current = nums2[j]
			j++
		}
	}
	if total%2 == 1 {
		return float64(current)
	}
	return float64(previous+current) / 2
}
