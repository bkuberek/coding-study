package word_ladder

func ladderLength(beginWord string, endWord string, wordList []string) int {
	available := make(map[string]bool, len(wordList))
	for _, word := range wordList {
		available[word] = true
	}
	if !available[endWord] {
		return 0
	}
	delete(available, beginWord)
	delete(available, endWord)
	// Two frontiers grow toward each other; words counts the ladder length covered so far.
	near, far := map[string]bool{beginWord: true}, map[string]bool{endWord: true}
	words := 1
	for len(near) > 0 && len(far) > 0 {
		if len(near) > len(far) {
			near, far = far, near // always expand the smaller frontier
		}
		words++
		followingLevel := make(map[string]bool)
		for word := range near {
			letters := []byte(word)
			for position, original := range letters {
				for letter := byte('a'); letter <= 'z'; letter++ {
					letters[position] = letter
					candidate := string(letters)
					if far[candidate] {
						return words
					}
					if available[candidate] {
						delete(available, candidate)
						followingLevel[candidate] = true
					}
				}
				letters[position] = original
			}
		}
		near = followingLevel
	}
	return 0
}
