package word_search

var steps = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

func exist(board [][]rune, word string) bool {
	letters := []rune(word)
	rows, cols := len(board), len(board[0])
	visited := make([][]bool, rows)
	for r := range visited {
		visited[r] = make([]bool, cols)
	}

	// spellsFrom reports whether letters[k:] can be spelled by a walk that starts at (r, c).
	var spellsFrom func(r, c, k int) bool
	spellsFrom = func(r, c, k int) bool {
		if r < 0 || r >= rows || c < 0 || c >= cols || visited[r][c] || board[r][c] != letters[k] {
			return false
		}
		if k == len(letters)-1 {
			return true
		}
		visited[r][c] = true
		found := false
		for _, step := range steps {
			if spellsFrom(r+step[0], c+step[1], k+1) {
				found = true
				break
			}
		}
		visited[r][c] = false
		return found
	}

	for r := 0; r < rows; r++ {
		for c := 0; c < cols; c++ {
			if spellsFrom(r, c, 0) {
				return true
			}
		}
	}
	return false
}
