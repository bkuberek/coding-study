package valid_sudoku

const (
	side    = 9
	boxSize = 3
	empty   = '.'
)

func isValidSudoku(board [][]rune) bool {
	// Bit d-1 of a mask is set once digit d has been seen in that row, column or box.
	var rows, columns, boxes [side]int
	for row := 0; row < side; row++ {
		for column := 0; column < side; column++ {
			digit := board[row][column]
			if digit == empty {
				continue
			}
			bit := 1 << (digit - '1')
			box := (row/boxSize)*boxSize + column/boxSize
			if (rows[row]|columns[column]|boxes[box])&bit != 0 {
				return false
			}
			rows[row] |= bit
			columns[column] |= bit
			boxes[box] |= bit
		}
	}
	return true
}
