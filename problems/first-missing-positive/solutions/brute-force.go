package first_missing_positive

import "slices"

func firstMissingPositive(nums []int) int {
	candidate := 1
	for slices.Contains(nums, candidate) {
		candidate++
	}
	return candidate
}
