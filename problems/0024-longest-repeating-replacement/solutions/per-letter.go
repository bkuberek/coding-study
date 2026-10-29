package longest_repeating_replacement

import "strings"

func characterReplacement(s string, k int) int {
	best := 0
	for target := byte('A'); target <= 'Z'; target++ {
		if strings.IndexByte(s, target) < 0 {
			continue // a letter that never occurs cannot start a better window
		}
		left, others := 0, 0
		for right := 0; right < len(s); right++ {
			if s[right] != target {
				others++
			}
			for others > k {
				if s[left] != target {
					others--
				}
				left++
			}
			best = max(best, right-left+1)
		}
	}
	return best
}
