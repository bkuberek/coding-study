package max_average_fixed_window

func maxWindowAverage(nums []int, k int) float64 {
	windowSum := 0
	for _, value := range nums[:k] {
		windowSum += value
	}
	best := windowSum
	for right := k; right < len(nums); right++ {
		// Slide one step: the number at `right` enters and the one k places back leaves.
		windowSum += nums[right] - nums[right-k]
		best = max(best, windowSum)
	}
	// Every window has k numbers, so the largest sum is the largest average. Divide once.
	return float64(best) / float64(k)
}
