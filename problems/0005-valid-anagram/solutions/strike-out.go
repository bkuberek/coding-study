package valid_anagram

import "bytes"

func isAnagram(s string, t string) bool {
	if len(s) != len(t) {
		return false
	}
	remaining := []byte(t)
	for i := 0; i < len(s); i++ {
		position := bytes.IndexByte(remaining, s[i])
		if position < 0 {
			return false
		}
		// A struck-out slot holds zero, which is never a lowercase letter.
		remaining[position] = 0
	}
	return true
}
