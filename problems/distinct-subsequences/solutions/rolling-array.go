package distinct_subsequences

func numDistinct(s string, t string) int {
	// ways[j] counts the occurrences of t[:j] in the prefix of s read so far.
	ways := make([]int, len(t)+1)
	ways[0] = 1
	for i := 0; i < len(s); i++ {
		// Right to left: ways[j-1] still excludes this character, so it is used once.
		for j := len(t); j > 0; j-- {
			if t[j-1] == s[i] {
				ways[j] += ways[j-1]
			}
		}
	}
	return ways[len(t)]
}
