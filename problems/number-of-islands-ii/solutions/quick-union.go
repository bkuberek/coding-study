package number_of_islands_ii

var steps = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

func numIslands2(m int, n int, positions [][]int) []int {
	parent := make([]int, m*n) // cell r * n + c; parent[x] == x marks a root
	for x := range parent {
		parent[x] = x
	}
	land := make([]bool, m*n)
	find := func(x int) int {
		for parent[x] != x {
			x = parent[x]
		}
		return x
	}

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
				if nr >= 0 && nr < m && nc >= 0 && nc < n && land[nr*n+nc] {
					rootNeighbor, rootCell := find(nr*n+nc), find(cell)
					if rootNeighbor != rootCell {
						parent[rootNeighbor] = rootCell // no balancing: chains can grow
						islands--
					}
				}
			}
		}
		counts = append(counts, islands)
	}
	return counts
}
