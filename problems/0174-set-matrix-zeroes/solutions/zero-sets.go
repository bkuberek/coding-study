package set_matrix_zeroes

func setZeroes(matrix [][]int) {
	// Find every row and column to clear before clearing anything.
	zeroRows := make(map[int]struct{})
	zeroCols := make(map[int]struct{})
	for r, row := range matrix {
		for c, value := range row {
			if value == 0 {
				zeroRows[r] = struct{}{}
				zeroCols[c] = struct{}{}
			}
		}
	}
	for r, row := range matrix {
		for c := range row {
			_, zeroRow := zeroRows[r]
			_, zeroCol := zeroCols[c]
			if zeroRow || zeroCol {
				row[c] = 0
			}
		}
	}
}
