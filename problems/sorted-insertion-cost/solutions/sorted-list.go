package sorted_insertion_cost

import (
	"slices"
	"sort"
)

const modulus = 1_000_000_007

func createSortedArray(instructions []int) int {
	ordered := make([]int, 0, len(instructions))
	cost := 0
	for _, value := range instructions {
		less := sort.SearchInts(ordered, value)
		atMost := sort.Search(len(ordered), func(i int) bool { return ordered[i] > value })
		greater := len(ordered) - atMost
		cost += min(less, greater)
		ordered = slices.Insert(ordered, atMost, value)
	}
	return cost % modulus
}
