package longest_consecutive_sequence

import "slices"

func longestConsecutive(nums []int) int {
	longest := 0
	for i, value := range nums {
		if slices.Contains(nums, value-1) {
			continue
		}
		if slices.Contains(nums[:i], value) {
			continue // an earlier copy of this start already counted its run
		}
		length := 1
		for slices.Contains(nums, value+length) {
			length++
		}
		longest = max(longest, length)
	}
	return longest
}
