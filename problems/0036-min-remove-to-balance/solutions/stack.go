package min_remove_to_balance

func minRemoveToMakeValid(s string) string {
	deleted := make([]bool, len(s))
	var openPositions []int
	for position := 0; position < len(s); position++ {
		switch s[position] {
		case '(':
			openPositions = append(openPositions, position)
		case ')':
			if len(openPositions) > 0 {
				// Matches the most recent unmatched opener.
				openPositions = openPositions[:len(openPositions)-1]
			} else {
				deleted[position] = true // nothing open: this closer can never match
			}
		}
	}
	for _, position := range openPositions {
		deleted[position] = true // openers that were never closed
	}
	result := make([]byte, 0, len(s))
	for position := 0; position < len(s); position++ {
		if !deleted[position] {
			result = append(result, s[position])
		}
	}
	return string(result)
}
