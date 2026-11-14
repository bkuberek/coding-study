package longest_substring_without_repeats

const asciiSize = 128

func lengthOfLongestSubstring(s string) int {
	var lastSeen [asciiSize]int
	for i := range lastSeen {
		lastSeen[i] = -1
	}
	left, best := 0, 0
	for right := 0; right < len(s); right++ {
		if previous := lastSeen[s[right]]; previous >= left {
			left = previous + 1
		}
		lastSeen[s[right]] = right
		best = max(best, right-left+1)
	}
	return best
}
