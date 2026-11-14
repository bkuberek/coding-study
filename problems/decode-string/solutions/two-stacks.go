package decode_string

func decodeString(s string) string {
	// For every open group: its repeat count and the text built before its "[".
	var counts []int
	var outerTexts [][]byte
	var current []byte
	count := 0
	for i := 0; i < len(s); i++ {
		character := s[i]
		switch {
		case '0' <= character && character <= '9':
			count = count*10 + int(character-'0')
		case character == '[':
			counts = append(counts, count)
			outerTexts = append(outerTexts, current)
			current = nil
			count = 0
		case character == ']':
			last := len(counts) - 1
			outer := outerTexts[last]
			for range counts[last] {
				outer = append(outer, current...)
			}
			current = outer
			counts, outerTexts = counts[:last], outerTexts[:last]
		default:
			current = append(current, character)
		}
	}
	return string(current)
}
