package set_matrix_zeroes

func setZeroes(matrix [][]int) {
	rows, cols := len(matrix), len(matrix[0])
	// matrix[r][0] marks row r (matrix[0][0] marks row 0) and matrix[0][c] marks column c
	// for c >= 1; column 0 needs its own flag, because matrix[0][0] is taken.
	firstColHasZero := false
	for r := 0; r < rows; r++ {
		if matrix[r][0] == 0 {
			firstColHasZero = true
		}
		for c := 1; c < cols; c++ {
			if matrix[r][c] == 0 {
				matrix[r][0] = 0
				matrix[0][c] = 0
			}
		}
	}
	// Bottom-up, so the markers in row 0 are read before row 0 itself is cleared.
	for r := rows - 1; r >= 0; r-- {
		for c := cols - 1; c > 0; c-- {
			if matrix[r][0] == 0 || matrix[0][c] == 0 {
				matrix[r][c] = 0
			}
		}
		if firstColHasZero {
			matrix[r][0] = 0
		}
	}
}
