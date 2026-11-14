package search_2d_matrix

func searchMatrix(matrix [][]int, target int) bool {
	for _, row := range matrix {
		for _, value := range row {
			if value == target {
				return true
			}
		}
	}
	return false
}
