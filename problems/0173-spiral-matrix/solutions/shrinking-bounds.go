package spiral_matrix

func spiralOrder(matrix [][]int) []int {
	top, bottom := 0, len(matrix)-1
	left, right := 0, len(matrix[0])-1
	order := make([]int, 0, len(matrix)*len(matrix[0]))
	for top <= bottom && left <= right {
		order = append(order, matrix[top][left:right+1]...)
		for r := top + 1; r <= bottom; r++ {
			order = append(order, matrix[r][right])
		}
		if top < bottom && left < right {
			// Only a ring with two rows and two columns has a bottom row and left column of its own.
			for c := right - 1; c >= left; c-- {
				order = append(order, matrix[bottom][c])
			}
			for r := bottom - 1; r > top; r-- {
				order = append(order, matrix[r][left])
			}
		}
		top, bottom, left, right = top+1, bottom-1, left+1, right-1
	}
	return order
}
