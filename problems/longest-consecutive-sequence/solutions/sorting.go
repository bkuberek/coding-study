package longest_consecutive_sequence

import "slices"

func longestConsecutive(nums []int) int {
	if len(nums) == 0 {
		return 0
	}
	ordered := slices.Clone(nums)
	slices.Sort(ordered)
	longest, current := 1, 1
	for i := 1; i < len(ordered); i++ {
		if ordered[i] == ordered[i-1] {
			continue
		}
		if ordered[i] == ordered[i-1]+1 {
			current++
		} else {
			current = 1
		}
		longest = max(longest, current)
	}
	return longest
}
