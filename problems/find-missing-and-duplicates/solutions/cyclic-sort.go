package find_missing_and_duplicates

func findMissingAndDuplicates(nums []int) [][]int {
	n := len(nums)
	for i := 0; i < n; i++ {
		// Swap nums[i] to its home index nums[i]-1 until the home already holds that value.
		// Comparing with the home, not with i, is what stops the loop on a repeated value.
		for nums[nums[i]-1] != nums[i] {
			home := nums[i] - 1
			nums[i], nums[home] = nums[home], nums[i]
		}
	}

	// Every value that occurs now sits at its home. A slot that holds another value is
	// either the home of a missing value or a spare copy of a value that is home elsewhere.
	// A negative sign on a home marks that its value has a spare copy.
	missing := []int{}
	for i := 0; i < n; i++ {
		if abs(nums[i]) == i+1 {
			continue
		}
		missing = append(missing, i+1)
		spare := nums[i]
		nums[spare-1] = -spare
	}

	// The marks are read in index order, so the duplicates come out sorted too.
	duplicated := []int{}
	for value := 1; value <= n; value++ {
		if nums[value-1] < 0 {
			duplicated = append(duplicated, value)
		}
	}
	return [][]int{missing, duplicated}
}

func abs(value int) int {
	if value < 0 {
		return -value
	}
	return value
}
