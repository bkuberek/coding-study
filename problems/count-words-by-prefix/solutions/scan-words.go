package count_words_by_prefix

import "strings"

func countByPrefix(words []string, prefixes []string) []int {
	counts := make([]int, len(prefixes))
	for i, prefix := range prefixes {
		for _, word := range words {
			if strings.HasPrefix(word, prefix) {
				counts[i]++
			}
		}
	}
	return counts
}
