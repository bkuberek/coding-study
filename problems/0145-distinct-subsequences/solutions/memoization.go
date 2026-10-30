package distinct_subsequences

func numDistinct(s string, t string) int {
	// ways[i][j] caches the occurrences of t[j:] as a subsequence of s[i:]; -1 is unknown.
	ways := make([][]int, len(s))
	for i := range ways {
		ways[i] = make([]int, len(t))
		for j := range ways[i] {
			ways[i][j] = -1
		}
	}
	var count func(i, j int) int
	count = func(i, j int) int {
		if j == len(t) {
			return 1 // the empty suffix of t occurs once
		}
		if len(s)-i < len(t)-j {
			return 0 // not enough characters left in s
		}
		if ways[i][j] < 0 {
			// Either s[i] is skipped, or it is matched with t[j].
			ways[i][j] = count(i+1, j)
			if s[i] == t[j] {
				ways[i][j] += count(i+1, j+1)
			}
		}
		return ways[i][j]
	}
	return count(0, 0)
}
