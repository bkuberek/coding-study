package split_array_largest_sum

import (
	"math"
	"slices"
)

func splitArray(nums []int, k int) int {
	n := len(nums)
	prefix := make([]int, n+1)
	for i, value := range nums {
		prefix[i+1] = prefix[i] + value
	}
	// best[i]: the smallest cost of cutting nums[:i] into the current number of pieces.
	best := slices.Clone(prefix)
	for pieces := 2; pieces <= k; pieces++ {
		next := make([]int, n+1)
		for end := pieces; end <= n; end++ {
			cheapest := math.MaxInt
			for cut := pieces - 1; cut < end; cut++ {
				cheapest = min(cheapest, max(best[cut], prefix[end]-prefix[cut]))
			}
			next[end] = cheapest
		}
		best = next
	}
	return best[n]
}
