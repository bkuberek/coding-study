package maximal_square

func maximalSquare(matrix [][]rune) int {
	rows, columns := len(matrix), len(matrix[0])
	// side[r][c] caches the largest all-ones square with its top-left corner at (r, c);
	// -1 is unknown.
	side := make([][]int, rows)
	for r := range side {
		side[r] = make([]int, columns)
		for c := range side[r] {
			side[r][c] = -1
		}
	}
	var largest func(r, c int) int
	largest = func(r, c int) int {
		if r == rows || c == columns || matrix[r][c] == '0' {
			return 0
		}
		if side[r][c] < 0 {
			side[r][c] = 1 + min(largest(r+1, c), largest(r, c+1), largest(r+1, c+1))
		}
		return side[r][c]
	}
	best := 0
	for r := 0; r < rows; r++ {
		for c := 0; c < columns; c++ {
			best = max(best, largest(r, c))
		}
	}
	return best * best
}
