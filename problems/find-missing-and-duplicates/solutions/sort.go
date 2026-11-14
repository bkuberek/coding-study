package find_missing_and_duplicates

import "slices"

func findMissingAndDuplicates(nums []int) [][]int {
	slices.Sort(nums)
	missing := []int{}
	duplicated := []int{}
	expected := 1 // the smallest value not accounted for yet
	previous := 0
	for _, value := range nums {
		if value == previous {
			// A third copy must not list the value again.
			if len(duplicated) == 0 || duplicated[len(duplicated)-1] != value {
				duplicated = append(duplicated, value)
			}
			continue
		}
		for ; expected < value; expected++ {
			missing = append(missing, expected)
		}
		expected = value + 1
		previous = value
	}
	for ; expected <= len(nums); expected++ {
		missing = append(missing, expected)
	}
	return [][]int{missing, duplicated}
}
