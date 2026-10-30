package subarray_sum_equals_k

func subarraySum(nums []int, k int) int {
	count := 0
	for start := range nums {
		total := 0
		for _, value := range nums[start:] {
			total += value
			if total == k {
				count++
			}
		}
	}
	return count
}
