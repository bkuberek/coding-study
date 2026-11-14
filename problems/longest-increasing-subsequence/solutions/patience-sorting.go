package longest_increasing_subsequence

import "slices"

func lengthOfLIS(nums []int) int {
	// tails[L-1] is the smallest last value of any increasing subsequence of length L seen
	// so far; it is strictly increasing, so it can be binary searched.
	tails := make([]int, 0, len(nums))
	for _, value := range nums {
		position, _ := slices.BinarySearch(tails, value)
		if position == len(tails) {
			tails = append(tails, value)
		} else {
			tails[position] = value
		}
	}
	return len(tails)
}
