package implement_trie

const alphabetSize = 26

type node struct {
	children [alphabetSize]*node
	isWord   bool
}

type Trie struct {
	root *node
}

func NewTrie() *Trie {
	return &Trie{root: &node{}}
}

func (t *Trie) Insert(word string) {
	current := t.root
	for _, letter := range word {
		slot := letter - 'a'
		if current.children[slot] == nil {
			current.children[slot] = &node{}
		}
		current = current.children[slot]
	}
	current.isWord = true
}

func (t *Trie) Search(word string) bool {
	last := t.walk(word)
	return last != nil && last.isWord
}

func (t *Trie) StartsWith(prefix string) bool {
	return t.walk(prefix) != nil
}

// walk returns the node at the end of the path spelled by text, or nil if the path breaks off.
func (t *Trie) walk(text string) *node {
	current := t.root
	for _, letter := range text {
		current = current.children[letter-'a']
		if current == nil {
			return nil
		}
	}
	return current
}
