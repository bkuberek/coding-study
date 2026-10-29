package bipartite_graph

type disjointSet struct {
	parent []int
	size   []int
}

func newDisjointSet(count int) *disjointSet {
	set := &disjointSet{parent: make([]int, count), size: make([]int, count)}
	for node := range set.parent {
		set.parent[node] = node
		set.size[node] = 1
	}
	return set
}

func (set *disjointSet) find(node int) int {
	root := node
	for set.parent[root] != root {
		root = set.parent[root]
	}
	for set.parent[node] != root {
		set.parent[node], node = root, set.parent[node]
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
	set.parent[rootB] = rootA
	set.size[rootA] += set.size[rootB]
}

func isBipartite(graph [][]int) bool {
	set := newDisjointSet(len(graph))
	// All neighbors of a node must share a team, so they go into one group.
	for _, neighbors := range graph {
		for i := 1; i < len(neighbors); i++ {
			set.union(neighbors[0], neighbors[i])
		}
	}
	// A split exists exactly when no edge has both ends in one group.
	for node, neighbors := range graph {
		for _, neighbor := range neighbors {
			if set.find(node) == set.find(neighbor) {
				return false
			}
		}
	}
	return true
}
