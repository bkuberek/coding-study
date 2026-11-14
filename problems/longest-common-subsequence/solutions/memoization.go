package longest_common_subsequence

func longestCommonSubsequence(text1 string, text2 string) int {
	// best[i][j] caches the answer for the suffixes text1[i:] and text2[j:]; -1 is unknown.
	best := make([][]int, len(text1))
	for i := range best {
		best[i] = make([]int, len(text2))
		for j := range best[i] {
			best[i][j] = -1
		}
	}
	var solve func(i, j int) int
	solve = func(i, j int) int {
		if i == len(text1) || j == len(text2) {
			return 0
		}
		if best[i][j] < 0 {
			if text1[i] == text2[j] {
				best[i][j] = 1 + solve(i+1, j+1)
			} else {
				best[i][j] = max(solve(i+1, j), solve(i, j+1))
			}
		}
		return best[i][j]
	}
	return solve(0, 0)
}
