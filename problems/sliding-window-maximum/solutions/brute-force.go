package sliding_window_maximum

func maxSlidingWindow(nums []int, k int) []int {
	maxima := make([]int, 0, len(nums)-k+1)
	for start := 0; start+k <= len(nums); start++ {
		largest := nums[start]
		for _, value := range nums[start+1 : start+k] {
			largest = max(largest, value)
		}
		maxima = append(maxima, largest)
	}
	return maxima
}
