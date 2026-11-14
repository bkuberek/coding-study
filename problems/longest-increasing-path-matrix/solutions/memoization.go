package longest_increasing_path_matrix

var steps = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

func longestIncreasingPath(matrix [][]int) int {
	rows, columns := len(matrix), len(matrix[0])
	// longest[r][c] caches the longest increasing path that starts at (r, c); 0 is unknown.
	longest := make([][]int, rows)
	for r := range longest {
		longest[r] = make([]int, columns)
	}
	var explore func(r, c int) int
	explore = func(r, c int) int {
		if longest[r][c] == 0 {
			best := 1
			for _, step := range steps {
				nr, nc := r+step[0], c+step[1]
				if nr >= 0 && nr < rows && nc >= 0 && nc < columns && matrix[nr][nc] > matrix[r][c] {
					best = max(best, 1+explore(nr, nc))
				}
			}
			longest[r][c] = best
		}
		return longest[r][c]
	}
	result := 0
	for r := 0; r < rows; r++ {
		for c := 0; c < columns; c++ {
			result = max(result, explore(r, c))
		}
	}
	return result
}
