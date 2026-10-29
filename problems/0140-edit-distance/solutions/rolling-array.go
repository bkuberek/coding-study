package edit_distance

func minDistance(word1 string, word2 string) int {
	// The distance is symmetric (insertions and deletions swap roles), so let the rows run
	// along the shorter word.
	longer, shorter := word1, word2
	if len(word1) < len(word2) {
		longer, shorter = word2, word1
	}
	// previous[j] is the distance between longer[:i-1] and shorter[:j]; current is the row
	// being filled, and the two swap after every character of longer.
	previous := make([]int, len(shorter)+1)
	current := make([]int, len(shorter)+1)
	for j := range previous {
		previous[j] = j
	}
	for i := 1; i <= len(longer); i++ {
		current[0] = i
		for j := 1; j <= len(shorter); j++ {
			if longer[i-1] == shorter[j-1] {
				current[j] = previous[j-1]
			} else {
				current[j] = 1 + min(previous[j], current[j-1], previous[j-1])
			}
		}
		previous, current = current, previous
	}
	return previous[len(shorter)]
}
