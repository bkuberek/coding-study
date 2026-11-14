package minimum_window_substring

const asciiSize = 128

func minWindow(s string, t string) string {
	var deficit [asciiSize]int
	for i := 0; i < len(t); i++ {
		deficit[t[i]]++
	}
	missing := len(t)
	bestStart, bestLength := 0, 0
	left := 0
	for right := 0; right < len(s); right++ {
		if deficit[s[right]] > 0 {
			missing--
		}
		deficit[s[right]]--
		for missing == 0 {
			if bestLength == 0 || right-left+1 < bestLength {
				bestStart, bestLength = left, right-left+1
			}
			deficit[s[left]]++
			if deficit[s[left]] > 0 {
				missing++
			}
			left++
		}
	}
	return s[bestStart : bestStart+bestLength]
}
