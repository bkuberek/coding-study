package continuous_subarray_sum

func checkSubarraySum(nums []int, k int) bool {
	for start := range nums {
		total := nums[start]
		for _, value := range nums[start+1:] {
			total += value
			if total%k == 0 {
				return true
			}
		}
	}
	return false
}
