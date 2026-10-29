package valid_sudoku

const (
	side    = 9
	boxSize = 3
	empty   = '.'
)

func isValidSudoku(board [][]rune) bool {
	for row := 0; row < side; row++ {
		for column := 0; column < side; column++ {
			digit := board[row][column]
			if digit != empty && repeats(board, row, column, digit) {
				return false
			}
		}
	}
	return true
}

// repeats reports whether another cell in the same row, column or box holds digit.
func repeats(board [][]rune, row, column int, digit rune) bool {
	top, left := row-row%boxSize, column-column%boxSize
	for i := 0; i < side; i++ {
		if i != column && board[row][i] == digit {
			return true
		}
		if i != row && board[i][column] == digit {
			return true
		}
		boxRow, boxColumn := top+i/boxSize, left+i%boxSize
		if (boxRow != row || boxColumn != column) && board[boxRow][boxColumn] == digit {
			return true
		}
	}
	return false
}
