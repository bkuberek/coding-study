package accounts_merge

import (
	"maps"
	"slices"
)

type disjointSet struct {
	parent []int
	size   []int // size[r]: number of accounts in the tree rooted at r
}

func newDisjointSet(count int) *disjointSet {
	set := &disjointSet{parent: make([]int, count), size: make([]int, count)}
	for x := range set.parent {
		set.parent[x] = x
		set.size[x] = 1
	}
	return set
}

func (set *disjointSet) find(x int) int {
	root := x
	for set.parent[root] != root {
		root = set.parent[root]
	}
	for set.parent[x] != root { // path compression: point the whole path at the root
		set.parent[x], x = root, set.parent[x]
	}
	return root
}

func (set *disjointSet) union(a, b int) {
	rootA, rootB := set.find(a), set.find(b)
	if rootA == rootB {
		return
	}
	if set.size[rootA] < set.size[rootB] {
		rootA, rootB = rootB, rootA
	}
	set.parent[rootB] = rootA // union by size: the smaller tree goes under the larger
	set.size[rootA] += set.size[rootB]
}

func accountsMerge(accounts [][]string) [][]string {
	set := newDisjointSet(len(accounts))
	firstOwner := make(map[string]int) // address -> first account that listed it
	for i, account := range accounts {
		for _, address := range account[1:] {
			owner, listed := firstOwner[address]
			if !listed {
				owner = i
				firstOwner[address] = i
			}
			set.union(owner, i)
		}
	}

	var roots []int // in the order each root first appears, so the output is stable
	addressesByRoot := make(map[int]map[string]bool)
	for i, account := range accounts {
		root := set.find(i)
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
