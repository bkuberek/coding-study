package wildcard_word_dictionary

const (
	alphabetSize = 26
	wildcard     = '.'
)

type node struct {
	children [alphabetSize]*node
	isWord   bool
}

type WordDictionary struct {
	root *node
}

func NewWordDictionary() *WordDictionary {
	return &WordDictionary{root: &node{}}
}

func (d *WordDictionary) AddWord(word string) {
	current := d.root
	for _, letter := range word {
		slot := letter - 'a'
		if current.children[slot] == nil {
			current.children[slot] = &node{}
		}
		current = current.children[slot]
	}
	current.isWord = true
}

func (d *WordDictionary) Search(word string) bool {
	return matchesFrom(d.root, word)
}

// matchesFrom reports whether some stored word continues from current the way pattern says.
func matchesFrom(current *node, pattern string) bool {
	for at := 0; at < len(pattern); at++ {
		if pattern[at] == wildcard {
			for _, child := range current.children {
				if child != nil && matchesFrom(child, pattern[at+1:]) {
					return true
				}
			}
			return false
		}
		current = current.children[pattern[at]-'a']
		if current == nil {
			return false
		}
	}
	return current.isWord
}
