package maximum_subarray

func maxSubArray(nums []int) int {
	best := nums[0]
	for start := range nums {
		total := 0
		for end := start; end < len(nums); end++ {
			total += nums[end]
			best = max(best, total)
		}
	}
	return best
}
