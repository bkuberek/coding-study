package sliding_window_maximum

func maxSlidingWindow(nums []int, k int) []int {
	maxima := make([]int, 0, len(nums)-k+1)
	// Positions whose values decrease from front to back; the front is the window's maximum.
	var candidates []int
	for right, value := range nums {
		for len(candidates) > 0 && nums[candidates[len(candidates)-1]] <= value {
			candidates = candidates[:len(candidates)-1]
		}
		candidates = append(candidates, right)
		if candidates[0] <= right-k {
			candidates = candidates[1:]
		}
		if right >= k-1 {
			maxima = append(maxima, nums[candidates[0]])
		}
	}
	return maxima
}
