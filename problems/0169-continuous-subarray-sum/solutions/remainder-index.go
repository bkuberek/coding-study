package continuous_subarray_sum

func checkSubarraySum(nums []int, k int) bool {
	// firstIndex[r] is the earliest position whose prefix (ending there) leaves remainder r;
	// the empty prefix ends at position -1.
	firstIndex := map[int]int{0: -1}
	remainder := 0
	for position, value := range nums {
		remainder = (remainder + value) % k
		earlier, seen := firstIndex[remainder]
		if !seen {
			firstIndex[remainder] = position
			continue
		}
		if position-earlier >= 2 {
			return true
		}
	}
	return false
}
