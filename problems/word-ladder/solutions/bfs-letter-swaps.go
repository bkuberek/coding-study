package word_ladder

type step struct {
	word       string
	wordsSoFar int
}

func ladderLength(beginWord string, endWord string, wordList []string) int {
	// Words still available; a word leaves the set the moment it is reached.
	available := make(map[string]bool, len(wordList))
	for _, word := range wordList {
		available[word] = true
	}
	if !available[endWord] {
		return 0
	}
	delete(available, beginWord)
	queue := []step{{beginWord, 1}}
	for len(queue) > 0 {
		current := queue[0]
		queue = queue[1:]
		if current.word == endWord {
			return current.wordsSoFar
		}
		letters := []byte(current.word)
		for position, original := range letters {
			for letter := byte('a'); letter <= 'z'; letter++ {
				letters[position] = letter
				candidate := string(letters)
				if available[candidate] {
					delete(available, candidate)
					queue = append(queue, step{candidate, current.wordsSoFar + 1})
				}
			}
			letters[position] = original
		}
	}
	return 0
}
