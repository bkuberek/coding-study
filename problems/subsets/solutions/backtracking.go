package subsets

import "slices"

func subsets(nums []int) [][]int {
	var result [][]int
	var chosen []int

	var explore func(index int)
	explore = func(index int) {
		if index == len(nums) {
			result = append(result, slices.Clone(chosen))
			return
		}
		chosen = append(chosen, nums[index])
		explore(index + 1)
		chosen = chosen[:len(chosen)-1]
		explore(index + 1)
	}

	explore(0)
	return result
}
