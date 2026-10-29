package edit_distance

func minDistance(word1 string, word2 string) int {
	// cost[i][j] caches the distance between the suffixes word1[i:] and word2[j:]; -1 is unknown.
	cost := make([][]int, len(word1)+1)
	for i := range cost {
		cost[i] = make([]int, len(word2)+1)
		for j := range cost[i] {
			cost[i][j] = -1
		}
	}
	var solve func(i, j int) int
	solve = func(i, j int) int {
		if i == len(word1) {
			return len(word2) - j // insert the rest of word2
		}
		if j == len(word2) {
			return len(word1) - i // delete the rest of word1
		}
		if cost[i][j] < 0 {
			if word1[i] == word2[j] {
				cost[i][j] = solve(i+1, j+1)
			} else {
				cost[i][j] = 1 + min(
					solve(i+1, j),   // delete word1[i]
					solve(i, j+1),   // insert word2[j]
					solve(i+1, j+1), // replace word1[i] with word2[j]
				)
			}
		}
		return cost[i][j]
	}
	return solve(0, 0)
}
