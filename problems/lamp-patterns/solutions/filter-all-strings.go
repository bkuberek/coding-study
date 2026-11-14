package lamp_patterns

import "strings"

func lampPatterns(n int) []string {
	var result []string
	pattern := make([]byte, n)
	for number := 0; number < 1<<n; number++ {
		// Counting up writes the strings in increasing order; the bits are the lamps.
		for i := range pattern {
			pattern[i] = '0' + byte(number>>(n-1-i)&1)
		}
		if !strings.Contains(string(pattern), "11") {
			result = append(result, string(pattern))
		}
	}
	return result
}
