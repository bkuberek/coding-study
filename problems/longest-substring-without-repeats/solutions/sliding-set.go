package longest_substring_without_repeats

const asciiSize = 128

func lengthOfLongestSubstring(s string) int {
	var inWindow [asciiSize]bool
	left, best := 0, 0
	for right := 0; right < len(s); right++ {
		for inWindow[s[right]] {
			inWindow[s[left]] = false
			left++
		}
		inWindow[s[right]] = true
		best = max(best, right-left+1)
	}
	return best
}
