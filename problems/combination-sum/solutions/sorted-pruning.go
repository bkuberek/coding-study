package combination_sum

import "slices"

func combinationSum(candidates []int, target int) [][]int {
	ordered := slices.Clone(candidates)
	slices.Sort(ordered)
	var result [][]int
	var chosen []int

	var extend func(start, remaining int)
	extend = func(start, remaining int) {
		if remaining == 0 {
			result = append(result, slices.Clone(chosen))
			return
		}
		// Values are added in non-decreasing order, so each combination is built once.
		for i := start; i < len(ordered); i++ {
			value := ordered[i]
			if value > remaining {
				break
			}
			chosen = append(chosen, value)
			extend(i, remaining-value)
			chosen = chosen[:len(chosen)-1]
		}
	}

	extend(0, target)
	return result
}
