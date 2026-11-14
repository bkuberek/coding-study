package maximal_square

func maximalSquare(matrix [][]rune) int {
	// side[c+1] is the largest square ending at column c of the current row (before the
	// update: of the row above); side[0] is a border of zeros.
	side := make([]int, len(matrix[0])+1)
	best := 0
	for _, row := range matrix {
		// diagonal is the row-above value of the previous column, saved before it is overwritten.
		diagonal := 0
		for c, cell := range row {
			above := side[c+1]
			if cell == '1' {
				side[c+1] = 1 + min(above, side[c], diagonal)
			} else {
				side[c+1] = 0
			}
			best = max(best, side[c+1])
			diagonal = above
		}
	}
	return best * best
}
