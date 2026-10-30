package interleaving_string

type verdict int8

const (
	unknown verdict = iota
	yes
	no
)

func isInterleave(s1 string, s2 string, s3 string) bool {
	if len(s1)+len(s2) != len(s3) {
		return false
	}
	// known[i][j] caches whether s1[i:] and s2[j:] interleave to s3[i+j:].
	known := make([][]verdict, len(s1)+1)
	for i := range known {
		known[i] = make([]verdict, len(s2)+1)
	}
	var solve func(i, j int) bool
	solve = func(i, j int) bool {
		if i == len(s1) && j == len(s2) {
			return true
		}
		if known[i][j] == unknown {
			// The next character of s3 comes from s1 or from s2.
			result := (i < len(s1) && s1[i] == s3[i+j] && solve(i+1, j)) ||
				(j < len(s2) && s2[j] == s3[i+j] && solve(i, j+1))
			known[i][j] = no
			if result {
				known[i][j] = yes
			}
		}
		return known[i][j] == yes
	}
	return solve(0, 0)
}
