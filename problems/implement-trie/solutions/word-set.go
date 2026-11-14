package implement_trie

import "strings"

type Trie struct {
	words map[string]struct{}
}

func NewTrie() *Trie {
	return &Trie{words: make(map[string]struct{})}
}

func (t *Trie) Insert(word string) {
	t.words[word] = struct{}{}
}

func (t *Trie) Search(word string) bool {
	_, found := t.words[word]
	return found
}

func (t *Trie) StartsWith(prefix string) bool {
	for word := range t.words {
		if strings.HasPrefix(word, prefix) {
			return true
		}
	}
	return false
}
