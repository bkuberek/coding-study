package word_search_ii

const used = '#'

var steps = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

func findWords(board [][]rune, words []string) []string {
	var found []string
	for _, word := range words {
		if onBoard(board, []rune(word)) {
			found = append(found, word)
		}
	}
	return found
}

func onBoard(board [][]rune, word []rune) bool {
	rows, cols := len(board), len(board[0])

	// trace reports whether word[position:] can be spelled starting at this cell.
	var trace func(row, col, position int) bool
	trace = func(row, col, position int) bool {
		if board[row][col] != word[position] {
			return false
		}
		if position == len(word)-1 {
			return true
		}
		board[row][col] = used
		found := false
		for _, step := range steps {
			r, c := row+step[0], col+step[1]
			if r >= 0 && r < rows && c >= 0 && c < cols && trace(r, c, position+1) {
				found = true
				break
			}
		}
		board[row][col] = word[position]
		return found
	}

	for row := 0; row < rows; row++ {
		for col := 0; col < cols; col++ {
			if trace(row, col, 0) {
				return true
			}
		}
	}
	return false
}
