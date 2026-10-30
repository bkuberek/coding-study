package word_search

import "slices"

const used = '#'

var steps = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

func exist(board [][]rune, word string) bool {
	rows, cols := len(board), len(board[0])
	var available, needed [26]int
	for _, row := range board {
		for _, letter := range row {
			available[letter-'a']++
		}
	}
	letters := []rune(word)
	for _, letter := range letters {
		needed[letter-'a']++
	}
	for i := range needed {
		if available[i] < needed[i] {
			return false
		}
	}
	// A walk read backwards is also a walk: start from whichever end is rarer on the board.
	if available[letters[0]-'a'] > available[letters[len(letters)-1]-'a'] {
		slices.Reverse(letters)
	}

	var spellsFrom func(r, c, k int) bool
	spellsFrom = func(r, c, k int) bool {
		if board[r][c] != letters[k] {
			return false
		}
		if k == len(letters)-1 {
			return true
		}
		board[r][c] = used
		found := false
		for _, step := range steps {
			nr, nc := r+step[0], c+step[1]
			if nr >= 0 && nr < rows && nc >= 0 && nc < cols && spellsFrom(nr, nc, k+1) {
				found = true
				break
			}
		}
		board[r][c] = letters[k]
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
