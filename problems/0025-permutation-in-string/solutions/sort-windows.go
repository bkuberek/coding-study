package permutation_in_string

import "slices"

func checkInclusion(pattern string, text string) bool {
	width := len(pattern)
	target := []byte(pattern)
	slices.Sort(target)
	for start := 0; start+width <= len(text); start++ {
		window := []byte(text[start : start+width])
		slices.Sort(window)
		if slices.Equal(window, target) {
			return true
		}
	}
	return false
}
