package regex_matching

type verdict int8

const (
	unknown verdict = iota
	yes
	no
)

func isMatch(s string, p string) bool {
	// known[i][j] caches whether s[i:] matches p[j:].
	known := make([][]verdict, len(s)+1)
	for i := range known {
		known[i] = make([]verdict, len(p)+1)
	}
	var solve func(i, j int) bool
	solve = func(i, j int) bool {
		if j == len(p) {
			return i == len(s)
		}
		if known[i][j] == unknown {
			first := i < len(s) && (p[j] == s[i] || p[j] == '.')
			var result bool
			if j+1 < len(p) && p[j+1] == '*' {
				// Skip "x*" entirely, or let it eat one more character and stay on it.
				result = solve(i, j+2) || (first && solve(i+1, j))
			} else {
				result = first && solve(i+1, j+1)
			}
			known[i][j] = no
			if result {
				known[i][j] = yes
			}
		}
		return known[i][j] == yes
	}
	return solve(0, 0)
}
