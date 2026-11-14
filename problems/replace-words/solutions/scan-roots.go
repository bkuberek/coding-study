package replace_words

import "strings"

func replaceWords(dictionary []string, sentence string) string {
	words := strings.Split(sentence, " ")
	shortened := make([]string, len(words))
	for i, word := range words {
		best := word
		for _, root := range dictionary {
			if len(root) < len(best) && strings.HasPrefix(word, root) {
				best = root
			}
		}
		shortened[i] = best
	}
	return strings.Join(shortened, " ")
}
