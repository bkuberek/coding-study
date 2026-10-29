package encode_decode_strings

import (
	"strconv"
	"strings"
)

const marker = '#'

func encode(strs []string) string {
	var builder strings.Builder
	for _, text := range strs {
		builder.WriteString(strconv.Itoa(len(text)))
		builder.WriteByte(marker)
		builder.WriteString(text)
	}
	return builder.String()
}

func decode(encoded string) []string {
	var strs []string
	position := 0
	for position < len(encoded) {
		// A length has only digits, so the first marker after it ends the length.
		markerAt := position + strings.IndexByte(encoded[position:], marker)
		length, _ := strconv.Atoi(encoded[position:markerAt])
		start := markerAt + 1
		end := start + length
		strs = append(strs, encoded[start:end])
		position = end
	}
	return strs
}

func encodeDecode(strs []string) []string {
	return decode(encode(strs))
}
