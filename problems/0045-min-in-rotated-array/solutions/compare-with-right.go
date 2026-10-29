package min_in_rotated_array

func findMin(nums []int) int {
	// Invariant: the index of the minimum lies in [low, high].
	low, high := 0, len(nums)-1
	for low < high {
		middle := low + (high-low)/2
		if nums[middle] > nums[high] {
			low = middle + 1
		} else {
			high = middle
		}
	}
	return nums[low]
}
