package n_queens

import (
	"math/bits"
	"strings"
)

func solveNQueens(n int) [][]string {
	full := 1<<n - 1
	var boards [][]string
	queenColumn := make([]int, 0, n)

	// Each mask marks the squares of the current row attacked along one kind of line.
	var place func(columns, diagonals, antiDiagonals int)
	place = func(columns, diagonals, antiDiagonals int) {
		if columns == full {
			boards = append(boards, draw(queenColumn))
			return
		}
		free := full &^ (columns | diagonals | antiDiagonals)
		for free != 0 {
			bit := free & -free // lowest free square
			free ^= bit
			queenColumn = append(queenColumn, bits.TrailingZeros(uint(bit)))
			// Moving one row down shifts each diagonal attack one column over.
			place(columns|bit, (diagonals|bit)<<1&full, (antiDiagonals|bit)>>1)
			queenColumn = queenColumn[:len(queenColumn)-1]
		}
	}

	place(0, 0, 0)
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
