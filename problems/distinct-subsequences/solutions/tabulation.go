package distinct_subsequences

func numDistinct(s string, t string) int {
	rows, columns := len(s), len(t)
	// ways[i][j] counts the occurrences of t[:j] in s[:i]; the empty t[:0] occurs once.
	ways := make([][]int, rows+1)
	for i := range ways {
		ways[i] = make([]int, columns+1)
		ways[i][0] = 1
	}
	for i := 1; i <= rows; i++ {
		for j := 1; j <= columns; j++ {
			// Occurrences that skip s[i-1], plus those that match it with t[j-1].
			ways[i][j] = ways[i-1][j]
			if s[i-1] == t[j-1] {
				ways[i][j] += ways[i-1][j-1]
			}
		}
	}
	return ways[rows][columns]
}
