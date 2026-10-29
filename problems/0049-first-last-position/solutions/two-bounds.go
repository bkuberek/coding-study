package first_last_position

func searchRange(nums []int, target int) []int {
	first := firstIndex(nums, func(value int) bool { return value >= target })
	if first == len(nums) || nums[first] != target {
		return []int{-1, -1}
	}
	return []int{first, firstIndex(nums, func(value int) bool { return value > target }) - 1}
}

// firstIndex returns the smallest index whose value satisfies the monotone predicate isPast,
// or len(nums) when none does.
func firstIndex(nums []int, isPast func(int) bool) int {
	low, high := 0, len(nums)
	for low < high {
		middle := low + (high-low)/2
		if isPast(nums[middle]) {
			high = middle
		} else {
			low = middle + 1
		}
	}
	return low
}
