package count_smaller_after_self

func countSmaller(nums []int) []int {
	counts := make([]int, len(nums))
	for i, value := range nums {
		for _, later := range nums[i+1:] {
			if later < value {
				counts[i]++
			}
		}
	}
	return counts
}
