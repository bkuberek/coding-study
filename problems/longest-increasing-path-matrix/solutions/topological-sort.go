package longest_increasing_path_matrix

var steps = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

func longestIncreasingPath(matrix [][]int) int {
	rows, columns := len(matrix), len(matrix[0])

	inGrid := func(r, c int) bool { return r >= 0 && r < rows && c >= 0 && c < columns }

	// larger[r][c] counts the neighbors a path could still step up to from (r, c).
	larger := make([][]int, rows)
	var layer [][2]int
	for r := range larger {
		larger[r] = make([]int, columns)
		for c := range larger[r] {
			for _, step := range steps {
				nr, nc := r+step[0], c+step[1]
				if inGrid(nr, nc) && matrix[nr][nc] > matrix[r][c] {
					larger[r][c]++
				}
			}
			if larger[r][c] == 0 {
				layer = append(layer, [2]int{r, c})
			}
		}
	}
	// Kahn's algorithm from the sinks: each round removes the cells whose larger neighbors are
	// all gone. A cell removed in round k starts a longest path of exactly k cells.
	rounds := 0
	for len(layer) > 0 {
		rounds++
		var nextLayer [][2]int
		for _, cell := range layer {
			r, c := cell[0], cell[1]
			for _, step := range steps {
				nr, nc := r+step[0], c+step[1]
				if inGrid(nr, nc) && matrix[nr][nc] < matrix[r][c] {
					larger[nr][nc]--
					if larger[nr][nc] == 0 {
						nextLayer = append(nextLayer, [2]int{nr, nc})
					}
				}
			}
		}
		layer = nextLayer
	}
	return rounds
}
