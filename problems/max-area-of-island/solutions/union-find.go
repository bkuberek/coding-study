package max_area_of_island

type disjointSet struct {
	parent []int
	size   []int
}

func newDisjointSet(count int) *disjointSet {
	set := &disjointSet{parent: make([]int, count), size: make([]int, count)}
	for cell := range set.parent {
		set.parent[cell] = cell
		set.size[cell] = 1
	}
	return set
}

func (set *disjointSet) find(cell int) int {
	root := cell
	for set.parent[root] != root {
		root = set.parent[root]
	}
	for set.parent[cell] != root {
		set.parent[cell], cell = root, set.parent[cell]
	}
	return root
}

// union merges the groups of a and b and returns the size of the merged group.
func (set *disjointSet) union(a, b int) int {
	rootA, rootB := set.find(a), set.find(b)
	if rootA != rootB {
		if set.size[rootA] < set.size[rootB] {
			rootA, rootB = rootB, rootA
		}
		set.parent[rootB] = rootA
		set.size[rootA] += set.size[rootB]
	}
	return set.size[rootA]
}

func maxAreaOfIsland(grid [][]int) int {
	rows, cols := len(grid), len(grid[0])
	set := newDisjointSet(rows * cols)
	best := 0
	for row := range grid {
		for col := range grid[row] {
			if grid[row][col] != 1 {
				continue
			}
			cell := row*cols + col
			best = max(best, 1)
			if col+1 < cols && grid[row][col+1] == 1 {
				best = max(best, set.union(cell, cell+1))
			}
			if row+1 < rows && grid[row+1][col] == 1 {
				best = max(best, set.union(cell, cell+cols))
			}
		}
	}
	return best
}
