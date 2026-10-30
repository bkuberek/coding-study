package n_queens

import "strings"

func solveNQueens(n int) [][]string {
	var boards [][]string
	// queenColumn[r] is the column of the queen in row r, for the rows placed so far.
	queenColumn := make([]int, 0, n)

	isSafe := func(row, col int) bool {
		for otherRow, otherCol := range queenColumn {
			if col == otherCol || abs(col-otherCol) == row-otherRow {
				return false
			}
		}
		return true
	}

	var place func(row int)
	place = func(row int) {
		if row == n {
			boards = append(boards, draw(queenColumn))
			return
		}
		for col := 0; col < n; col++ {
			if isSafe(row, col) {
				queenColumn = append(queenColumn, col)
				place(row + 1)
				queenColumn = queenColumn[:len(queenColumn)-1]
			}
		}
	}

	place(0)
	return boards
}

func abs(value int) int {
	if value < 0 {
		return -value
	}
	return value
}

// draw renders one board, one string per row, from the column of each row's queen.
func draw(queenColumn []int) []string {
	size := len(queenColumn)
	rows := make([]string, size)
	for row, col := range queenColumn {
		rows[row] = strings.Repeat(".", col) + "Q" + strings.Repeat(".", size-col-1)
	}
	return rows
}
