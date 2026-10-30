package regex_matching

// fits reports whether the pattern letter matches the character.
func fits(letter, character byte) bool {
	return letter == character || letter == '.'
}

func isMatch(s string, p string) bool {
	columns := len(p)
	// previous[j]: s[:i-1] matches p[:j]; current[j]: s[:i] matches p[:j]. The two swap after
	// every character of s; row 0 never reads previous, and every cell of current is rewritten.
	previous := make([]bool, columns+1)
	current := make([]bool, columns+1)
	for i := 0; i <= len(s); i++ {
		current[0] = i == 0
		for j := 1; j <= columns; j++ {
			if p[j-1] == '*' {
				// "x*" matches nothing, or it matches s[i-1] and possibly more before it.
				current[j] = current[j-2] || (i > 0 && fits(p[j-2], s[i-1]) && previous[j])
			} else {
				current[j] = i > 0 && fits(p[j-1], s[i-1]) && previous[j-1]
			}
		}
		previous, current = current, previous
	}
	return previous[columns]
}
