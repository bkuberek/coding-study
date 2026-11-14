package substring_search

func findAllOccurrences(text string, pattern string) []int {
	var found []int
	for start := 0; start+len(pattern) <= len(text); start++ {
		offset := 0
		for offset < len(pattern) && text[start+offset] == pattern[offset] {
			offset++
		}
		if offset == len(pattern) {
			found = append(found, start)
		}
	}
	return found
}
