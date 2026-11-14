package max_product_subarray

func maxProduct(nums []int) int {
	// Within a zero-free run, the best product is a prefix or a suffix of the run, so the
	// running products from both ends (restarted after each zero) cover every candidate.
	best := nums[0]
	for _, value := range nums {
		best = max(best, value)
	}
	fromLeft, fromRight := 1, 1
	n := len(nums)
	for i := 0; i < n; i++ {
		if fromLeft == 0 {
			fromLeft = 1
		}
		if fromRight == 0 {
			fromRight = 1
		}
		fromLeft *= nums[i]
		fromRight *= nums[n-1-i]
		best = max(best, fromLeft, fromRight)
	}
	return best
}
