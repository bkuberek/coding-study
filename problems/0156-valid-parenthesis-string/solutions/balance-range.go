package valid_parenthesis_string

func checkValidString(s string) bool {
	// The possible open counts of the prefix are exactly the integers in [lowest, highest].
	lowest, highest := 0, 0
	for i := 0; i < len(s); i++ {
		switch s[i] {
		case '(':
			lowest++
			highest++
		case ')':
			lowest--
			highest--
		default:
			lowest--  // the wildcard as ")"
			highest++ // the wildcard as "("
		}
		if highest < 0 {
			return false // even with every wildcard as "(", too many ")"
		}
		lowest = max(lowest, 0) // a negative count is not a real choice
	}
	return lowest == 0
}
