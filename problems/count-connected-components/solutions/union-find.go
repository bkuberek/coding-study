package count_connected_components

func countComponents(n int, edges [][]int) int {
	parent := make([]int, n)
	size := make([]int, n) // size[r]: number of nodes in the tree rooted at r
	for x := range parent {
		parent[x] = x
		size[x] = 1
	}
	find := func(x int) int {
		root := x
		for parent[root] != root {
			root = parent[root]
		}
		for parent[x] != root { // path compression: point the whole path at the root
			parent[x], x = root, parent[x]
		}
		return root
	}
	components := n
	for _, edge := range edges {
		rootA, rootB := find(edge[0]), find(edge[1])
		if rootA == rootB {
			continue
		}
		if size[rootA] < size[rootB] {
			rootA, rootB = rootB, rootA
		}
		parent[rootB] = rootA // union by size: the smaller tree goes under the larger
		size[rootA] += size[rootB]
		components--
	}
	return components
}
