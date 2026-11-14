package maximum_subarray

func maxSubArray(nums []int) int {
	// endingHere is the best sum of a subarray that ends at the current index.
	endingHere, best := nums[0], nums[0]
	for _, value := range nums[1:] {
		endingHere = max(value, endingHere+value)
		best = max(best, endingHere)
	}
	return best
}
