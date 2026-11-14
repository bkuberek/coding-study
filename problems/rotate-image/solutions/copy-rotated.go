package rotate_image

func rotate(matrix [][]int) {
	n := len(matrix)
	// Row r of the rotated image is column r of the original, read from bottom to top.
	rotated := make([][]int, n)
	for r := range rotated {
		rotated[r] = make([]int, n)
		for c := range rotated[r] {
			rotated[r][c] = matrix[n-1-c][r]
		}
	}
	copy(matrix, rotated)
}
