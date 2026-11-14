package replace_words

import "strings"

type trieNode struct {
	children [26]*trieNode
	end      bool // a root ends at this node
}

func replaceWords(dictionary []string, sentence string) string {
	root := &trieNode{}
	for _, word := range dictionary {
		node := root
		for i := 0; i < len(word); i++ {
			letter := word[i] - 'a'
			if node.children[letter] == nil {
				node.children[letter] = &trieNode{}
			}
			node = node.children[letter]
		}
		node.end = true
	}

	words := strings.Split(sentence, " ")
	for i, word := range words {
		words[i] = shorten(root, word)
	}
	return strings.Join(words, " ")
}

// shorten returns the shortest root that prefixes word, or word itself.
func shorten(root *trieNode, word string) string {
	node := root
	for length := 0; length < len(word); length++ {
		if node.end {
			return word[:length]
		}
		node = node.children[word[length]-'a']
		if node == nil {
			return word
		}
	}
	return word
}
