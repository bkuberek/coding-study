package valid_sudoku

const (
	side    = 9
	boxSize = 3
	empty   = '.'
)

func isValidSudoku(board [][]rune) bool {
	var rows, columns, boxes [side]map[rune]bool
	for i := 0; i < side; i++ {
		rows[i], columns[i], boxes[i] = map[rune]bool{}, map[rune]bool{}, map[rune]bool{}
	}
	for row := 0; row < side; row++ {
		for column := 0; column < side; column++ {
			digit := board[row][column]
			if digit == empty {
				continue
			}
			box := (row/boxSize)*boxSize + column/boxSize
			if rows[row][digit] || columns[column][digit] || boxes[box][digit] {
				return false
			}
			rows[row][digit] = true
			columns[column][digit] = true
			boxes[box][digit] = true
		}
	}
	return true
}
