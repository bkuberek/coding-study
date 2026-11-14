package majority_element

import "slices"

func majorityElement(nums []int) int {
	sorted := slices.Clone(nums)
	slices.Sort(sorted)
	// The majority block covers more than half of the sorted positions, so it covers the middle.
	return sorted[len(sorted)/2]
}
