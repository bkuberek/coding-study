package longest_common_subsequence

func longestCommonSubsequence(text1 string, text2 string) int {
	rows, columns := len(text1), len(text2)
	// best[i][j] is the answer for the prefixes text1[:i] and text2[:j]; row and column 0
	// stand for an empty prefix.
	best := make([][]int, rows+1)
	for i := range best {
		best[i] = make([]int, columns+1)
	}
	for i := 1; i <= rows; i++ {
		for j := 1; j <= columns; j++ {
			if text1[i-1] == text2[j-1] {
				best[i][j] = best[i-1][j-1] + 1
			} else {
				best[i][j] = max(best[i-1][j], best[i][j-1])
			}
		}
	}
	return best[rows][columns]
}
