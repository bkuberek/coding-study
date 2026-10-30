package permutations

import "slices"

func permute(nums []int) [][]int {
	values := slices.Clone(nums)
	var result [][]int

	// values[:slot] is the fixed prefix; values[slot:] are the candidates still free.
	var fixSlot func(slot int)
	fixSlot = func(slot int) {
		if slot == len(values) {
			result = append(result, slices.Clone(values))
			return
		}
		for candidate := slot; candidate < len(values); candidate++ {
			values[slot], values[candidate] = values[candidate], values[slot]
			fixSlot(slot + 1)
			values[slot], values[candidate] = values[candidate], values[slot]
		}
	}

	fixSlot(0)
	return result
}
