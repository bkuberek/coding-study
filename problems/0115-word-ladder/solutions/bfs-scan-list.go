package word_ladder

import "slices"

type step struct {
	word       string
	wordsSoFar int
}

func oneApart(first, second string) bool {
	differences := 0
	for i := 0; i < len(first) && i < len(second); i++ {
		if first[i] != second[i] {
			differences++
			if differences > 1 {
				return false
			}
		}
	}
	return differences == 1
}

func ladderLength(beginWord string, endWord string, wordList []string) int {
	if !slices.Contains(wordList, endWord) {
		return 0
	}
	unvisited := make([]string, 0, len(wordList))
	for _, word := range wordList {
		if word != beginWord {
			unvisited = append(unvisited, word)
		}
	}
	queue := []step{{beginWord, 1}}
	for len(queue) > 0 {
		current := queue[0]
		queue = queue[1:]
		if current.word == endWord {
			return current.wordsSoFar
		}
		// Compare against every word not reached yet; the neighbors leave the list.
		remaining := make([]string, 0, len(unvisited))
		for _, candidate := range unvisited {
			if oneApart(current.word, candidate) {
				queue = append(queue, step{candidate, current.wordsSoFar + 1})
			} else {
				remaining = append(remaining, candidate)
			}
		}
		unvisited = remaining
	}
	return 0
}
