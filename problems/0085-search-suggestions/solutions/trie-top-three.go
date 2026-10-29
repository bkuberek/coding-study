package search_suggestions

import "slices"

const (
	alphabetSize = 26
	shown        = 3
)

type node struct {
	children [alphabetSize]*node
	smallest []string
}

func suggestedProducts(products []string, searchWord string) [][]string {
	root := &node{}
	ordered := slices.Clone(products)
	slices.Sort(ordered)
	// Inserting in sorted order means each node's first three products are its smallest.
	for _, product := range ordered {
		current := root
		for _, letter := range product {
			slot := letter - 'a'
			if current.children[slot] == nil {
				current.children[slot] = &node{}
			}
			current = current.children[slot]
			if len(current.smallest) < shown {
				current.smallest = append(current.smallest, product)
			}
		}
	}
	suggestions := make([][]string, 0, len(searchWord))
	cursor := root
	for _, letter := range searchWord {
		if cursor != nil {
			cursor = cursor.children[letter-'a']
		}
		var suggestion []string
		if cursor != nil {
			suggestion = slices.Clone(cursor.smallest)
		}
		suggestions = append(suggestions, suggestion)
	}
	return suggestions
}
