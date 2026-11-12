package substring_search

import "strings"

const (
	base    int64 = 131
	modulus int64 = 1_000_000_007
)

func findAllOccurrences(text string, pattern string) []int {
	windowSize := len(pattern)
	if windowSize > len(text) {
		return nil
	}
	leavingWeight := int64(1)
	for i := 1; i < windowSize; i++ {
		leavingWeight = leavingWeight * base % modulus
	}
	var target, window int64
	for i := 0; i < windowSize; i++ {
		target = (target*base + int64(pattern[i])) % modulus
		window = (window*base + int64(text[i])) % modulus
	}
	var found []int
	for start := 0; start+windowSize <= len(text); start++ {
		if window == target && strings.HasPrefix(text[start:], pattern) {
			found = append(found, start)
		}
		if start+windowSize < len(text) {
			without := (window - int64(text[start])*leavingWeight%modulus + modulus) % modulus
			window = (without*base + int64(text[start+windowSize])) % modulus
		}
	}
	return found
}
