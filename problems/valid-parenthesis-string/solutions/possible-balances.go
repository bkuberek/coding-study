package valid_parenthesis_string

func checkValidString(s string) bool {
	// possible[k] is true when some choice of wildcards leaves k parentheses open after the
	// prefix; following is the same table for the next prefix. No count exceeds len(s).
	possible := make([]bool, len(s)+1)
	following := make([]bool, len(s)+1)
	possible[0] = true
	for i := 0; i < len(s); i++ {
		symbol := s[i]
		clear(following)
		reachable := false
		for open, ok := range possible {
			if !ok {
				continue
			}
			if symbol == '(' || symbol == '*' {
				following[open+1] = true
				reachable = true
			}
			if (symbol == ')' || symbol == '*') && open > 0 {
				following[open-1] = true
				reachable = true
			}
			if symbol == '*' {
				following[open] = true
				reachable = true
			}
		}
		possible, following = following, possible
		if !reachable {
			return false
		}
	}
	return possible[0]
}
