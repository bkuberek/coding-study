package longest_substring_without_repeats

const asciiSize = 128

func lengthOfLongestSubstring(s string) int {
	best := 0
	for start := 0; start < len(s); start++ {
		var seen [asciiSize]bool
		end := start
		for end < len(s) && !seen[s[end]] {
			seen[s[end]] = true
			end++
		}
		best = max(best, end-start)
	}
	return best
}
