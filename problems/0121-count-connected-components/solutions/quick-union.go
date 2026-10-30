package count_connected_components

func countComponents(n int, edges [][]int) int {
	parent := make([]int, n) // parent[x] == x marks a root
	for x := range parent {
		parent[x] = x
	}
	find := func(x int) int {
		for parent[x] != x {
			x = parent[x]
		}
		return x
	}
	components := n
	for _, edge := range edges {
		rootA, rootB := find(edge[0]), find(edge[1])
		if rootA != rootB {
			parent[rootA] = rootB // no balancing: trees can grow into long chains
			components--
		}
	}
	return components
}
