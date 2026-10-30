package maximal_square

func maximalSquare(matrix [][]rune) int {
	rows, columns := len(matrix), len(matrix[0])
	// side[r+1][c+1] is the largest all-ones square with its bottom-right corner at (r, c);
	// row 0 and column 0 are a border of zeros.
	side := make([][]int, rows+1)
	for r := range side {
		side[r] = make([]int, columns+1)
	}
	best := 0
	for r := 0; r < rows; r++ {
		for c := 0; c < columns; c++ {
			if matrix[r][c] == '1' {
				side[r+1][c+1] = 1 + min(side[r][c+1], side[r+1][c], side[r][c])
				best = max(best, side[r+1][c+1])
			}
		}
	}
	return best * best
}
