package valid_anagram

import "slices"

func isAnagram(s string, t string) bool {
	if len(s) != len(t) {
		return false
	}
	left, right := []byte(s), []byte(t)
	slices.Sort(left)
	slices.Sort(right)
	return slices.Equal(left, right)
}
