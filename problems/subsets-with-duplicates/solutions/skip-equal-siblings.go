package subsets_with_duplicates

import "slices"

func subsetsWithDup(nums []int) [][]int {
	ordered := slices.Clone(nums)
	slices.Sort(ordered)
	var result [][]int
	var chosen []int

	var extend func(start int)
	extend = func(start int) {
		// Every node of this recursion is a distinct subset.
		result = append(result, slices.Clone(chosen))
		for i := start; i < len(ordered); i++ {
			// A second copy at the same level would rebuild the first copy's subtree.
			if i > start && ordered[i] == ordered[i-1] {
				continue
			}
			chosen = append(chosen, ordered[i])
			extend(i + 1)
			chosen = chosen[:len(chosen)-1]
		}
	}

	extend(0)
	return result
}
