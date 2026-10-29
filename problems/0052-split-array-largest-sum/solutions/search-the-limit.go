package split_array_largest_sum

import "slices"

func splitArray(nums []int, k int) int {
	// Feasibility only improves as the limit grows: find the smallest feasible limit.
	low, high := slices.Max(nums), 0
	for _, value := range nums {
		high += value
	}
	for low < high {
		limit := low + (high-low)/2
		if piecesNeeded(nums, limit) <= k {
			high = limit
		} else {
			low = limit + 1
		}
	}
	return low
}

// piecesNeeded greedily extends the current piece while it fits under the limit.
func piecesNeeded(nums []int, limit int) int {
	pieces, running := 1, 0
	for _, value := range nums {
		if running+value > limit {
			pieces++
			running = value
		} else {
			running += value
		}
	}
	return pieces
}
