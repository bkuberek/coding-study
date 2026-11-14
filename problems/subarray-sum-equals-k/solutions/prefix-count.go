package subarray_sum_equals_k

func subarraySum(nums []int, k int) int {
	// seen[s] counts the prefixes seen so far whose sum is s; the empty prefix sums to 0.
	seen := map[int]int{0: 1}
	total := 0
	count := 0
	for _, value := range nums {
		total += value
		// A missing key reads as 0 without being inserted.
		count += seen[total-k]
		seen[total]++
	}
	return count
}
