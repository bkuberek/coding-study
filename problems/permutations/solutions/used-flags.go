package permutations

import "slices"

func permute(nums []int) [][]int {
	var result [][]int
	var ordering []int
	used := make([]bool, len(nums))

	var fillNextSlot func()
	fillNextSlot = func() {
		if len(ordering) == len(nums) {
			result = append(result, slices.Clone(ordering))
			return
		}
		for i, value := range nums {
			if used[i] {
				continue
			}
			used[i] = true
			ordering = append(ordering, value)
			fillNextSlot()
			ordering = ordering[:len(ordering)-1]
			used[i] = false
		}
	}

	fillNextSlot()
	return result
}
