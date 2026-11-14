package word_break

type trieNode struct {
	children [26]*trieNode
	endsWord bool
}

func wordBreak(s string, wordDict []string) bool {
	root := &trieNode{}
	for _, word := range wordDict {
		node := root
		for i := 0; i < len(word); i++ {
			index := word[i] - 'a'
			if node.children[index] == nil {
				node.children[index] = &trieNode{}
			}
			node = node.children[index]
		}
		node.endsWord = true
	}

	// reachable[i] is true when the prefix s[:i] can be split into dictionary words.
	reachable := make([]bool, len(s)+1)
	reachable[0] = true
	for start := 0; start < len(s); start++ {
		if !reachable[start] {
			continue
		}
		node := root
		for position := start; position < len(s); position++ {
			node = node.children[s[position]-'a']
			if node == nil {
				break
			}
			if node.endsWord {
				reachable[position+1] = true
			}
		}
	}
	return reachable[len(s)]
}
