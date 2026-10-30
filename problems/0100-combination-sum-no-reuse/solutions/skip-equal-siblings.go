package combination_sum_no_reuse

import "slices"

func combinationSum2(candidates []int, target int) [][]int {
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
		for i := start; i < len(ordered); i++ {
			value := ordered[i]
			if value > remaining {
				break
			}
			// A second copy at the same level would rebuild the first copy's combinations.
			if i > start && value == ordered[i-1] {
				continue
			}
			chosen = append(chosen, value)
			extend(i+1, remaining-value)
			chosen = chosen[:len(chosen)-1]
		}
	}

	extend(0, target)
	return result
}
