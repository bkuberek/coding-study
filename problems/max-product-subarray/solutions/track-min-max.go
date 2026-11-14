package max_product_subarray

func maxProduct(nums []int) int {
	// largest and smallest are the extreme products of subarrays that end at the current index.
	largest, smallest, best := nums[0], nums[0], nums[0]
	for _, value := range nums[1:] {
		extendLargest, extendSmallest := largest*value, smallest*value
		largest = max(value, extendLargest, extendSmallest)
		smallest = min(value, extendLargest, extendSmallest)
		best = max(best, largest)
	}
	return best
}
