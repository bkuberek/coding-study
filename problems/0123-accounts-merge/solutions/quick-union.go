package accounts_merge

import (
	"maps"
	"slices"
)

func accountsMerge(accounts [][]string) [][]string {
	parent := make([]int, len(accounts)) // parent[x] == x marks a root
	for x := range parent {
		parent[x] = x
	}
	find := func(x int) int {
		for parent[x] != x {
			x = parent[x]
		}
		return x
	}

	firstOwner := make(map[string]int) // address -> first account that listed it
	for i, account := range accounts {
		for _, address := range account[1:] {
			owner, listed := firstOwner[address]
			if !listed {
				owner = i
				firstOwner[address] = i
			}
			rootOwner, rootHere := find(owner), find(i)
			if rootOwner != rootHere {
				parent[rootOwner] = rootHere // no balancing: trees can grow into long chains
			}
		}
	}

	var roots []int // in the order each root first appears, so the output is stable
	addressesByRoot := make(map[int]map[string]bool)
	for i, account := range accounts {
		root := find(i)
		if _, known := addressesByRoot[root]; !known {
			addressesByRoot[root] = make(map[string]bool)
			roots = append(roots, root)
		}
		for _, address := range account[1:] {
			addressesByRoot[root][address] = true
		}
	}
	merged := make([][]string, 0, len(roots))
	for _, root := range roots {
		person := []string{accounts[root][0]}
		merged = append(merged, append(person, slices.Sorted(maps.Keys(addressesByRoot[root]))...))
	}
	return merged
}
