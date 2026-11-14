package binary_search

func search(nums []int, target int) int {
	// Invariant: if target is in nums, its index lies in [low, high].
	low, high := 0, len(nums)-1
	for low <= high {
		middle := low + (high-low)/2
		switch {
		case nums[middle] == target:
			return middle
		case nums[middle] < target:
			low = middle + 1
		default:
			high = middle - 1
		}
	}
	return -1
}
