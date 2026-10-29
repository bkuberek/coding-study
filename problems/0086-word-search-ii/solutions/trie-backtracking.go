package word_search_ii

const (
	alphabetSize = 26
	used         = '#'
)

var steps = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

type node struct {
	children [alphabetSize]*node
	// word is the complete word that ends at this node, or "" once it has been reported.
	word string
}

func findWords(board [][]rune, words []string) []string {
	root := &node{}
	for _, word := range words {
		current := root
		for _, letter := range word {
			slot := letter - 'a'
			if current.children[slot] == nil {
				current.children[slot] = &node{}
			}
			current = current.children[slot]
		}
		current.word = word
	}
	rows, cols := len(board), len(board[0])
	var found []string

	var explore func(row, col int, parent *node)
	explore = func(row, col int, parent *node) {
		letter := board[row][col]
		if letter == used {
			return
		}
		current := parent.children[letter-'a']
		if current == nil {
			return
		}
		if current.word != "" {
			found = append(found, current.word)
			current.word = ""
		}
		board[row][col] = used
		for _, step := range steps {
			r, c := row+step[0], col+step[1]
			if r >= 0 && r < rows && c >= 0 && c < cols {
				explore(r, c, current)
			}
		}
		board[row][col] = letter
	}

	for row := 0; row < rows; row++ {
		for col := 0; col < cols; col++ {
			explore(row, col, root)
		}
	}
	return found
}
