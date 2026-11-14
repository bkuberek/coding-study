package search_suggestions

import (
	"slices"
	"strings"
)

const shown = 3

func suggestedProducts(products []string, searchWord string) [][]string {
	suggestions := make([][]string, 0, len(searchWord))
	for typed := 1; typed <= len(searchWord); typed++ {
		prefix := searchWord[:typed]
		var matches []string
		for _, product := range products {
			if strings.HasPrefix(product, prefix) {
				matches = append(matches, product)
			}
		}
		slices.Sort(matches)
		suggestions = append(suggestions, matches[:min(shown, len(matches))])
	}
	return suggestions
}
