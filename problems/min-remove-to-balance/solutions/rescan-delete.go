package min_remove_to_balance

import "slices"

func minRemoveToMakeValid(s string) string {
	text := []byte(s)
	for position := firstOffender(text); position != -1; position = firstOffender(text) {
		text = slices.Delete(text, position, position+1) // shifts the rest of the text: O(n)
	}
	return string(text)
}

// firstOffender returns a parenthesis that cannot be matched, or -1 when the text is balanced.
func firstOffender(text []byte) int {
	depth := 0
	for position, character := range text {
		switch character {
		case '(':
			depth++
		case ')':
			if depth == 0 {
				return position // a closer with nothing open before it
			}
			depth--
		}
	}
	if depth == 0 {
		return -1
	}
	// Some openers are never closed: the last opener with no closer left after it is one.
	closers := 0
	for position := len(text) - 1; position >= 0; position-- {
		switch text[position] {
		case ')':
			closers++
		case '(':
			if closers == 0 {
				return position
			}
			closers--
		}
	}
	return -1
}
