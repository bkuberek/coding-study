package minimum_window_substring

const asciiSize = 128

func minWindow(s string, t string) string {
	var need [asciiSize]int
	for i := 0; i < len(t); i++ {
		need[t[i]]++
	}
	bestStart, bestLength := 0, 0
	for start := 0; start < len(s); start++ {
		remaining := need // arrays are values: this copies the table
		missing := len(t)
		for end := start; end < len(s); end++ {
			if remaining[s[end]] > 0 {
				missing--
			}
			remaining[s[end]]--
			if missing == 0 {
				if bestLength == 0 || end-start+1 < bestLength {
					bestStart, bestLength = start, end-start+1
				}
				break
			}
		}
	}
	return s[bestStart : bestStart+bestLength]
}
