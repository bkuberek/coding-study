package max_product_subarray

func maxProduct(nums []int) int {
	best := nums[0]
	for start := range nums {
		product := 1
		for end := start; end < len(nums); end++ {
			product *= nums[end]
			best = max(best, product)
		}
	}
	return best
}
