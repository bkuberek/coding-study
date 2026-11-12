package substring_search

func findAllOccurrences(text string, pattern string) []int {
	border := borderTable(pattern)
	var found []int
	matched := 0
	for position := 0; position < len(text); position++ {
		for matched > 0 && text[position] != pattern[matched] {
			matched = border[matched-1]
		}
		if text[position] == pattern[matched] {
			matched++
		}
		if matched == len(pattern) {
			found = append(found, position-len(pattern)+1)
			matched = border[matched-1]
		}
	}
	return found
}

// borderTable[i] is the length of the longest proper prefix of pattern[:i+1] that is also a suffix of it.
func borderTable(pattern string) []int {
	border := make([]int, len(pattern))
	length := 0
	for i := 1; i < len(pattern); i++ {
		for length > 0 && pattern[i] != pattern[length] {
			length = border[length-1]
		}
		if pattern[i] == pattern[length] {
			length++
		}
		border[i] = length
	}
	return border
}
