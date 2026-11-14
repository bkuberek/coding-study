package maximal_rectangle

func maximalRectangle(matrix [][]rune) int {
	rows, columns := len(matrix), len(matrix[0])
	// width[r][c] is the number of consecutive ones ending at (r, c) in row r.
	width := make([][]int, rows)
	for r := range width {
		width[r] = make([]int, columns)
	}
	best := 0
	for r := 0; r < rows; r++ {
		for c := 0; c < columns; c++ {
			if matrix[r][c] == '0' {
				continue
			}
			width[r][c] = 1
			if c > 0 {
				width[r][c] = width[r][c-1] + 1
			}
			// Rectangles with bottom-right corner (r, c): extend upwards one row at a time; the
			// rectangle is as wide as the narrowest row it spans.
			narrowest := width[r][c]
			for top := r; top >= 0; top-- {
				narrowest = min(narrowest, width[top][c])
				if narrowest == 0 {
					break
				}
				best = max(best, narrowest*(r-top+1))
			}
		}
	}
	return best
}
