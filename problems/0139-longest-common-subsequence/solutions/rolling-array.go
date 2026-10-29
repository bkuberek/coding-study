package longest_common_subsequence

func longestCommonSubsequence(text1 string, text2 string) int {
	// The answer is symmetric, so let the rows run along the shorter string.
	longer, shorter := text1, text2
	if len(text1) < len(text2) {
		longer, shorter = text2, text1
	}
	// previous[j] is the answer for the prefixes longer[:i] and shorter[:j]; current is the
	// row being filled, and the two swap after every character of longer.
	previous := make([]int, len(shorter)+1)
	current := make([]int, len(shorter)+1)
	for i := 0; i < len(longer); i++ {
		for j := 1; j <= len(shorter); j++ {
			if longer[i] == shorter[j-1] {
				current[j] = previous[j-1] + 1
			} else {
				current[j] = max(previous[j], current[j-1])
			}
		}
		previous, current = current, previous
	}
	return previous[len(shorter)]
}
