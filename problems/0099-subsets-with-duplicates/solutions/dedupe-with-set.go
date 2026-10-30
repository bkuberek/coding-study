package subsets_with_duplicates

import (
	"slices"
	"strconv"
)

func subsetsWithDup(nums []int) [][]int {
	ordered := slices.Clone(nums)
	slices.Sort(ordered)
	// Taking values in sorted order gives every multiset one canonical key to dedupe on.
	// Slices are not comparable, so the key is the subset's text.
	distinct := make(map[string][]int)
	for mask := 0; mask < 1<<len(ordered); mask++ {
		var subset []int
		var key []byte
		for i, value := range ordered {
			if mask>>i&1 == 1 {
				subset = append(subset, value)
				key = strconv.AppendInt(key, int64(value), 10)
				key = append(key, ',')
			}
		}
		if _, seen := distinct[string(key)]; !seen {
			distinct[string(key)] = subset
		}
	}
	result := make([][]int, 0, len(distinct))
	for _, subset := range distinct {
		result = append(result, subset)
	}
	return result
}
