package decode_string

import "strings"

func decodeString(s string) string {
	decoded, _ := decodeGroup(s, 0)
	return decoded
}

// decodeGroup decodes from position up to the "]" that closes the current group, or to the end
// of s. It returns the decoded text and the position just after that "]".
func decodeGroup(s string, position int) (string, int) {
	var decoded strings.Builder
	count := 0
	for position < len(s) {
		character := s[position]
		position++
		switch {
		case '0' <= character && character <= '9':
			count = count*10 + int(character-'0')
		case character == '[':
			var inner string
			inner, position = decodeGroup(s, position)
			decoded.WriteString(strings.Repeat(inner, count))
			count = 0
		case character == ']':
			return decoded.String(), position
		default:
			decoded.WriteByte(character)
		}
	}
	return decoded.String(), position
}
