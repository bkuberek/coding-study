package longest_increasing_path_matrix

import "sort"

var steps = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

func longestIncreasingPath(matrix [][]int) int {
	rows, columns := len(matrix), len(matrix[0])
	// longest[r][c] is the longest increasing path starting at (r, c).
	longest := make([][]int, rows)
	order := make([][2]int, 0, rows*columns)
	for r := range longest {
		longest[r] = make([]int, columns)
		for c := range longest[r] {
			longest[r][c] = 1
			order = append(order, [2]int{r, c})
		}
	}
	// Every larger neighbor comes earlier in decreasing order of value, so its entry is final
	// when the cell is processed. Equal neighbors are never steps, so ties may go either way.
	sort.Slice(order, func(a, b int) bool {
		return matrix[order[a][0]][order[a][1]] > matrix[order[b][0]][order[b][1]]
	})
	result := 0
	for _, cell := range order {
		r, c := cell[0], cell[1]
		for _, step := range steps {
			nr, nc := r+step[0], c+step[1]
			if nr >= 0 && nr < rows && nc >= 0 && nc < columns && matrix[nr][nc] > matrix[r][c] {
				longest[r][c] = max(longest[r][c], 1+longest[nr][nc])
			}
		}
		result = max(result, longest[r][c])
	}
	return result
}
