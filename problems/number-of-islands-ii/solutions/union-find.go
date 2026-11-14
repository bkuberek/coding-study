package number_of_islands_ii

var steps = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

type disjointSet struct {
	parent []int
	size   []int // size[r]: number of cells in the tree rooted at r
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

// union merges the groups of a and b and reports whether they were separate.
func (set *disjointSet) union(a, b int) bool {
	rootA, rootB := set.find(a), set.find(b)
	if rootA == rootB {
		return false
	}
	if set.size[rootA] < set.size[rootB] {
		rootA, rootB = rootB, rootA
	}
	set.parent[rootB] = rootA // union by size: the smaller tree goes under the larger
	set.size[rootA] += set.size[rootB]
	return true
}

func numIslands2(m int, n int, positions [][]int) []int {
	set := newDisjointSet(m * n) // cell r * n + c
	land := make([]bool, m*n)

	islands := 0
	counts := make([]int, 0, len(positions))
	for _, position := range positions {
		r, c := position[0], position[1]
		cell := r*n + c
		if !land[cell] {
			land[cell] = true
			islands++ // a new island, until it merges with its neighbors
			for _, step := range steps {
				nr, nc := r+step[0], c+step[1]
				if nr >= 0 && nr < m && nc >= 0 && nc < n && land[nr*n+nc] && set.union(nr*n+nc, cell) {
					islands--
				}
			}
		}
		counts = append(counts, islands)
	}
	return counts
}
