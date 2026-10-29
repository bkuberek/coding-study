package min_size_subarray_sum

import "slices"

func minSubArrayLen(target int, nums []int) int {
	// prefix[i] is the sum of nums[:i]; the values are strictly increasing.
	prefix := make([]int, len(nums)+1)
	for i, value := range nums {
		prefix[i+1] = prefix[i] + value
	}
	best := 0
	for start := range nums {
		offset, _ := slices.BinarySearch(prefix[start+1:], prefix[start]+target)
		end := start + 1 + offset
		if end < len(prefix) && (best == 0 || end-start < best) {
			best = end - start
		}
	}
	return best
}
