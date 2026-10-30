package maximal_rectangle

func maximalRectangle(matrix [][]rune) int {
	columns := len(matrix[0])
	// For the current row and each column c: height[c] consecutive ones end here in column c,
	// and the rectangle of that height through column c spans columns left[c] .. right[c]-1.
	height := make([]int, columns)
	left := make([]int, columns)
	right := make([]int, columns)
	for c := range right {
		right[c] = columns
	}
	best := 0
	for _, row := range matrix {
		boundary := 0 // first column after the last zero seen in this row
		for c := 0; c < columns; c++ {
			if row[c] == '1' {
				height[c]++
				left[c] = max(left[c], boundary)
			} else {
				height[c], left[c], boundary = 0, 0, c+1
			}
		}
		boundary = columns // the last zero seen from the right
		for c := columns - 1; c >= 0; c-- {
			if row[c] == '1' {
				right[c] = min(right[c], boundary)
			} else {
				right[c], boundary = columns, c
			}
		}
		for c := 0; c < columns; c++ {
			best = max(best, height[c]*(right[c]-left[c]))
		}
	}
	return best
}
