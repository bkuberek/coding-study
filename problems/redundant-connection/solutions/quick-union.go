package redundant_connection

func findRedundantConnection(edges [][]int) []int {
	parent := make([]int, len(edges)+1) // parent[x] == x marks a root
	for x := range parent {
		parent[x] = x
	}
	find := func(x int) int {
		for parent[x] != x {
			x = parent[x]
		}
		return x
	}
	for _, edge := range edges {
		a, b := edge[0], edge[1]
		rootA, rootB := find(a), find(b)
		if rootA == rootB {
			return []int{a, b} // the ends are already connected: this edge closes the cycle
		}
		parent[rootA] = rootB // no balancing: trees can grow into long chains
	}
	return nil
}
