package missing_number

import "slices"

func missingNumber(nums []int) int {
	sorted := slices.Clone(nums)
	slices.Sort(sorted)
	// In the sorted array, value i sits at index i until the gap.
	for index, value := range sorted {
		if value != index {
			return index
		}
	}
	return len(nums)
}
