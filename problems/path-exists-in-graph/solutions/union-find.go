package path_exists_in_graph

func hasPath(n int, edges [][]int, source int, target int) bool {
	parent := make([]int, n)
	size := make([]int, n)
	for node := range parent {
		parent[node] = node
		size[node] = 1
	}
	find := func(node int) int {
		// Path halving: point every other node on the way up at its grandparent.
		for parent[node] != node {
			parent[node] = parent[parent[node]]
			node = parent[node]
		}
		return node
	}
	for _, edge := range edges {
		rootA, rootB := find(edge[0]), find(edge[1])
		if rootA == rootB {
			continue
		}
		if size[rootA] < size[rootB] {
			rootA, rootB = rootB, rootA
		}
		parent[rootB] = rootA
		size[rootA] += size[rootB]
	}
	return find(source) == find(target)
}
