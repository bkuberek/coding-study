package search_suggestions

import (
	"slices"
	"strings"
)

const shown = 3

func suggestedProducts(products []string, searchWord string) [][]string {
	ordered := slices.Clone(products)
	slices.Sort(ordered)
	suggestions := make([][]string, 0, len(searchWord))
	start := 0
	for typed := 1; typed <= len(searchWord); typed++ {
		prefix := searchWord[:typed]
		// Products starting with prefix form one block; it begins at the first product >= prefix.
		// A longer prefix never begins its block earlier, so the search can start at start.
		offset, _ := slices.BinarySearch(ordered[start:], prefix)
		start += offset
		var block []string
		for _, product := range ordered[start:min(start+shown, len(ordered))] {
			if strings.HasPrefix(product, prefix) {
				block = append(block, product)
			}
		}
		suggestions = append(suggestions, block)
	}
	return suggestions
}
