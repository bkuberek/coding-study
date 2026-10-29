package binary_search

func search(nums []int, target int) int {
	// Find the first index whose value is >= target, in the half-open range [low, high).
	low, high := 0, len(nums)
	for low < high {
		middle := low + (high-low)/2
		if nums[middle] < target {
			low = middle + 1
		} else {
			high = middle
		}
	}
	if low < len(nums) && nums[low] == target {
		return low
	}
	return -1
}
