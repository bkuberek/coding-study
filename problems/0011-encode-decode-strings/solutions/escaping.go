package encode_decode_strings

import "strings"

const (
	escape     = '\\'
	terminator = ','
)

func encode(strs []string) string {
	var builder strings.Builder
	for _, text := range strs {
		for i := 0; i < len(text); i++ {
			if text[i] == escape || text[i] == terminator {
				builder.WriteByte(escape)
			}
			builder.WriteByte(text[i])
		}
		builder.WriteByte(terminator)
	}
	return builder.String()
}

func decode(encoded string) []string {
	var strs []string
	var current strings.Builder
	escaped := false
	for i := 0; i < len(encoded); i++ {
		character := encoded[i]
		switch {
		case escaped:
			current.WriteByte(character)
			escaped = false
		case character == escape:
			escaped = true
		case character == terminator:
			strs = append(strs, current.String())
			current.Reset()
		default:
			current.WriteByte(character)
		}
	}
	return strs
}

func encodeDecode(strs []string) []string {
	return decode(encode(strs))
}
