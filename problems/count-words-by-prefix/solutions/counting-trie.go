package count_words_by_prefix

const alphabetSize = 26

type node struct {
	children [alphabetSize]*node
	passing  int // how many words go through this node
}

func countByPrefix(words []string, prefixes []string) []int {
	root := &node{}
	for _, word := range words {
		current := root
		for _, letter := range word {
			slot := letter - 'a'
			if current.children[slot] == nil {
				current.children[slot] = &node{}
			}
			current = current.children[slot]
			current.passing++
		}
	}

	counts := make([]int, len(prefixes))
	for i, prefix := range prefixes {
		current := root
		for _, letter := range prefix {
			current = current.children[letter-'a']
			if current == nil {
				break // the path breaks off: no word begins with this prefix
			}
		}
		if current != nil {
			counts[i] = current.passing
		}
	}
	return counts
}
