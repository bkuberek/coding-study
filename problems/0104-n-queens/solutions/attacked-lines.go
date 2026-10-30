package n_queens

import "strings"

func solveNQueens(n int) [][]string {
	var boards [][]string
	queenColumn := make([]int, 0, n)
	columns := make([]bool, n)
	// Squares on one diagonal share row - col; on one anti-diagonal they share row + col.
	// row - col runs from -(n-1) to n-1, so it is stored shifted by n - 1.
	diagonals := make([]bool, 2*n-1)
	antiDiagonals := make([]bool, 2*n-1)

	var place func(row int)
	place = func(row int) {
		if row == n {
			boards = append(boards, draw(queenColumn))
			return
		}
		for col := 0; col < n; col++ {
			diagonal, antiDiagonal := row-col+n-1, row+col
			if columns[col] || diagonals[diagonal] || antiDiagonals[antiDiagonal] {
				continue
			}
			columns[col], diagonals[diagonal], antiDiagonals[antiDiagonal] = true, true, true
			queenColumn = append(queenColumn, col)
			place(row + 1)
			queenColumn = queenColumn[:len(queenColumn)-1]
			columns[col], diagonals[diagonal], antiDiagonals[antiDiagonal] = false, false, false
		}
	}

	place(0)
	return boards
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
