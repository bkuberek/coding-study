package rotate_image

import "slices"

func rotate(matrix [][]int) {
	n := len(matrix)
	// Reflect across the main diagonal, then mirror every row left to right.
	for r := 0; r < n; r++ {
		for c := r + 1; c < n; c++ {
			matrix[r][c], matrix[c][r] = matrix[c][r], matrix[r][c]
		}
	}
	for _, row := range matrix {
		slices.Reverse(row)
	}
}
