package combination_sum

import "slices"

func combinationSum(candidates []int, target int) [][]int {
	var result [][]int
	var chosen []int

	var explore func(index, remaining int)
	explore = func(index, remaining int) {
		if remaining == 0 {
			result = append(result, slices.Clone(chosen))
			return
		}
		if remaining < 0 || index == len(candidates) {
			return
		}
		// Use candidates[index] once more and stay on it, since it may repeat.
		chosen = append(chosen, candidates[index])
		explore(index, remaining-candidates[index])
		chosen = chosen[:len(chosen)-1]
		// Or never use it again.
		explore(index+1, remaining)
	}

	explore(0, target)
	return result
}
