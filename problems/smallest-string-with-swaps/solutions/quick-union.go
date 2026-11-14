package smallest_string_with_swaps

import "slices"

func smallestStringWithSwaps(s string, pairs [][]int) string {
	parent := make([]int, len(s)) // parent[x] == x marks a root
	for x := range parent {
		parent[x] = x
	}
	find := func(x int) int {
		for parent[x] != x {
			x = parent[x]
		}
		return x
	}

	for _, pair := range pairs {
		rootA, rootB := find(pair[0]), find(pair[1])
		if rootA != rootB {
			parent[rootA] = rootB // no balancing: trees can grow into long chains
		}
	}

	// Positions are visited in increasing order, so each group's list is sorted.
	groups := make([][]int, len(s))
	for position := range len(s) {
		root := find(position)
		groups[root] = append(groups[root], position)
	}
	letters := []byte(s)
	for _, positions := range groups {
		sorted := make([]byte, len(positions))
		for i, position := range positions {
			sorted[i] = s[position]
		}
		slices.Sort(sorted)
		for i, position := range positions {
			letters[position] = sorted[i]
		}
	}
	return string(letters)
}
