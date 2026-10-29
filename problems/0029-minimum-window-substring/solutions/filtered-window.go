package minimum_window_substring

const asciiSize = 128

func minWindow(s string, t string) string {
	var deficit [asciiSize]int
	for i := 0; i < len(t); i++ {
		deficit[t[i]]++
	}
	// The positions of the letters that t contains: the window slides over these only.
	var useful []int
	for i := 0; i < len(s); i++ {
		if deficit[s[i]] > 0 {
			useful = append(useful, i)
		}
	}
	missing := len(t)
	bestStart, bestLength := 0, 0
	left := 0
	for _, right := range useful {
		if deficit[s[right]] > 0 {
			missing--
		}
		deficit[s[right]]--
		for missing == 0 {
			start := useful[left]
			if bestLength == 0 || right-start+1 < bestLength {
				bestStart, bestLength = start, right-start+1
			}
			deficit[s[start]]++
			if deficit[s[start]] > 0 {
				missing++
			}
			left++
		}
	}
	return s[bestStart : bestStart+bestLength]
}
