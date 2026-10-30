package number_of_islands

const land = '1'

func numIslands(grid [][]rune) int {
	rows, cols := len(grid), len(grid[0])
	parent := make([]int, rows*cols)
	size := make([]int, rows*cols)
	for cell := range parent {
		parent[cell] = cell
		size[cell] = 1
	}

	find := func(cell int) int {
		root := cell
		for parent[root] != root {
			root = parent[root]
		}
		for parent[cell] != root {
			parent[cell], cell = root, parent[cell]
		}
		return root
	}

	union := func(a, b int) bool {
		rootA, rootB := find(a), find(b)
		if rootA == rootB {
			return false
		}
		if size[rootA] < size[rootB] {
			rootA, rootB = rootB, rootA
		}
		parent[rootB] = rootA
		size[rootA] += size[rootB]
		return true
	}

	islands := 0
	for row := 0; row < rows; row++ {
		for col := 0; col < cols; col++ {
			if grid[row][col] != land {
				continue
			}
			islands++
			cell := row*cols + col
			// Looking right and down is enough: the left and upper neighbors already looked here.
			if col+1 < cols && grid[row][col+1] == land && union(cell, cell+1) {
				islands--
			}
			if row+1 < rows && grid[row+1][col] == land && union(cell, cell+cols) {
				islands--
			}
		}
	}
	return islands
}
