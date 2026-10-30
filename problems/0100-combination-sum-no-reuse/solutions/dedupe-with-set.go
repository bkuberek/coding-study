package combination_sum_no_reuse

import (
	"slices"
	"strconv"
)

func combinationSum2(candidates []int, target int) [][]int {
	ordered := slices.Clone(candidates)
	slices.Sort(ordered)
	// Values taken in sorted order give each multiset one canonical key. Slices are not
	// comparable, so the key is the combination's text.
	found := make(map[string][]int)
	for mask := 0; mask < 1<<len(ordered); mask++ {
		var chosen []int
		var key []byte
		sum := 0
		for i, value := range ordered {
			if mask>>i&1 == 1 {
				chosen = append(chosen, value)
				sum += value
				key = strconv.AppendInt(key, int64(value), 10)
				key = append(key, ',')
			}
		}
		if sum == target {
			found[string(key)] = chosen
		}
	}
	result := make([][]int, 0, len(found))
	for _, combination := range found {
		result = append(result, combination)
	}
	return result
}
