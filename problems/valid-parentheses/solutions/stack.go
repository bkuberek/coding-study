package valid_parentheses

var openerOf = map[rune]rune{')': '(', ']': '[', '}': '{'}

func isValid(s string) bool {
	var openBrackets []rune
	for _, character := range s {
		opener, isCloser := openerOf[character]
		if !isCloser {
			openBrackets = append(openBrackets, character)
			continue
		}
		last := len(openBrackets) - 1
		if last < 0 || openBrackets[last] != opener {
			return false
		}
		openBrackets = openBrackets[:last]
	}
	return len(openBrackets) == 0
}
