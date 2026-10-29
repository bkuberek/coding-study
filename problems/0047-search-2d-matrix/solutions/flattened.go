package search_2d_matrix

func searchMatrix(matrix [][]int, target int) bool {
	columns := len(matrix[0])
	low, high := 0, len(matrix)*columns-1
	for low <= high {
		middle := low + (high-low)/2
		value := matrix[middle/columns][middle%columns]
		switch {
		case value == target:
			return true
		case value < target:
			low = middle + 1
		default:
			high = middle - 1
		}
	}
	return false
}
