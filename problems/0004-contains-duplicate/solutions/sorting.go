package contains_duplicate

import "slices"

func containsDuplicate(nums []int) bool {
	sorted := slices.Clone(nums)
	slices.Sort(sorted)
	for i := 1; i < len(sorted); i++ {
		if sorted[i] == sorted[i-1] {
			return true
		}
	}
	return false
}
