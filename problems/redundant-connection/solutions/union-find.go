package redundant_connection

func findRedundantConnection(edges [][]int) []int {
	parent := make([]int, len(edges)+1)
	size := make([]int, len(edges)+1) // size[r]: number of nodes in the tree rooted at r
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
	for _, edge := range edges {
		a, b := edge[0], edge[1]
		rootA, rootB := find(a), find(b)
		if rootA == rootB {
			return []int{a, b} // the ends are already connected: this edge closes the cycle
		}
		if size[rootA] < size[rootB] {
			rootA, rootB = rootB, rootA
		}
		parent[rootB] = rootA // union by size: the smaller tree goes under the larger
		size[rootA] += size[rootB]
	}
	return nil
}
