package find_missing_and_duplicates

func findMissingAndDuplicates(nums []int) [][]int {
	seen := make(map[int]bool, len(nums))
	repeated := make(map[int]bool)
	for _, value := range nums {
		if seen[value] {
			repeated[value] = true
		}
		seen[value] = true
	}
	// Walking 1..n instead of the maps keeps both answers sorted without a sort.
	missing := []int{}
	duplicated := []int{}
	for value := 1; value <= len(nums); value++ {
		if !seen[value] {
			missing = append(missing, value)
		}
		if repeated[value] {
			duplicated = append(duplicated, value)
		}
	}
	return [][]int{missing, duplicated}
}
