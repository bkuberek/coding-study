package surrounded_regions

const safe = 'S'

func solve(board [][]rune) {
	rows, cols := len(board), len(board[0])
	// Every 'O' on the edge is safe; so is everything connected to one of them.
	var stack [][2]int
	for r := range board {
		for c := range board[r] {
			onEdge := r == 0 || r == rows-1 || c == 0 || c == cols-1
			if onEdge && board[r][c] == 'O' {
				board[r][c] = safe
				stack = append(stack, [2]int{r, c})
			}
		}
	}
	steps := [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}
	for len(stack) > 0 {
		cell := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		for _, step := range steps {
			nr, nc := cell[0]+step[0], cell[1]+step[1]
			if nr >= 0 && nr < rows && nc >= 0 && nc < cols && board[nr][nc] == 'O' {
				board[nr][nc] = safe
				stack = append(stack, [2]int{nr, nc})
			}
		}
	}
	for _, row := range board {
		for c, cell := range row {
			if cell == safe {
				row[c] = 'O'
			} else {
				row[c] = 'X'
			}
		}
	}
}
