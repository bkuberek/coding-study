package regex_matching

// fits reports whether the pattern letter matches the character.
func fits(letter, character byte) bool {
	return letter == character || letter == '.'
}

func isMatch(s string, p string) bool {
	rows, columns := len(s), len(p)
	// matches[i][j]: s[:i] matches p[:j].
	matches := make([][]bool, rows+1)
	for i := range matches {
		matches[i] = make([]bool, columns+1)
	}
	matches[0][0] = true
	for i := 0; i <= rows; i++ {
		for j := 1; j <= columns; j++ {
			if p[j-1] == '*' {
				// "x*" matches nothing, or it matches s[i-1] and possibly more before it.
				matches[i][j] = matches[i][j-2] || (i > 0 && fits(p[j-2], s[i-1]) && matches[i-1][j])
			} else {
				matches[i][j] = i > 0 && fits(p[j-1], s[i-1]) && matches[i-1][j-1]
			}
		}
	}
	return matches[rows][columns]
}
