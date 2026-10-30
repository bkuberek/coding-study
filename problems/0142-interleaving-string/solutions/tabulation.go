package interleaving_string

func isInterleave(s1 string, s2 string, s3 string) bool {
	rows, columns := len(s1), len(s2)
	if rows+columns != len(s3) {
		return false
	}
	// reach[i][j]: s1[:i] and s2[:j] interleave to s3[:i+j].
	reach := make([][]bool, rows+1)
	for i := range reach {
		reach[i] = make([]bool, columns+1)
	}
	reach[0][0] = true
	for i := 0; i <= rows; i++ {
		for j := 0; j <= columns; j++ {
			// The last character of s3[:i+j] came from s1 or from s2.
			if i > 0 && reach[i-1][j] && s1[i-1] == s3[i+j-1] {
				reach[i][j] = true
			} else if j > 0 && reach[i][j-1] && s2[j-1] == s3[i+j-1] {
				reach[i][j] = true
			}
		}
	}
	return reach[rows][columns]
}
