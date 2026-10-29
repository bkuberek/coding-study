package search_2d_matrix

func searchMatrix(matrix [][]int, target int) bool {
	// Everything left of the current cell in its row is smaller or equal; everything
	// below it in its column is larger or equal.
	row, column := 0, len(matrix[0])-1
	for row < len(matrix) && column >= 0 {
		value := matrix[row][column]
		switch {
		case value == target:
			return true
		case value > target:
			column--
		default:
			row++
		}
	}
	return false
}
