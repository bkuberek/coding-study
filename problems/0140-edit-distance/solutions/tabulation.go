package edit_distance

func minDistance(word1 string, word2 string) int {
	rows, columns := len(word1), len(word2)
	// cost[i][j] is the distance between the prefixes word1[:i] and word2[:j]. Turning a prefix
	// into the empty word takes one deletion per character, and the reverse one insertion.
	cost := make([][]int, rows+1)
	for i := range cost {
		cost[i] = make([]int, columns+1)
		cost[i][0] = i
	}
	for j := range cost[0] {
		cost[0][j] = j
	}
	for i := 1; i <= rows; i++ {
		for j := 1; j <= columns; j++ {
			if word1[i-1] == word2[j-1] {
				cost[i][j] = cost[i-1][j-1]
			} else {
				cost[i][j] = 1 + min(cost[i-1][j], cost[i][j-1], cost[i-1][j-1])
			}
		}
	}
	return cost[rows][columns]
}
