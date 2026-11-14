package wildcard_word_dictionary

import "strings"

const wildcard = '.'

type WordDictionary struct {
	byLength map[int]map[string]struct{}
}

func NewWordDictionary() *WordDictionary {
	return &WordDictionary{byLength: make(map[int]map[string]struct{})}
}

func (d *WordDictionary) AddWord(word string) {
	bucket, ok := d.byLength[len(word)]
	if !ok {
		bucket = make(map[string]struct{})
		d.byLength[len(word)] = bucket
	}
	bucket[word] = struct{}{}
}

func (d *WordDictionary) Search(word string) bool {
	candidates := d.byLength[len(word)]
	if strings.IndexByte(word, wildcard) < 0 {
		_, found := candidates[word]
		return found
	}
	for candidate := range candidates {
		if matches(word, candidate) {
			return true
		}
	}
	return false
}

// matches compares a pattern with a stored word of the same length.
func matches(pattern, word string) bool {
	for i := 0; i < len(pattern); i++ {
		if pattern[i] != wildcard && pattern[i] != word[i] {
			return false
		}
	}
	return true
}
