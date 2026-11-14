package decode_string

import (
	"strconv"
	"strings"
)

func decodeString(s string) string {
	for strings.IndexByte(s, '[') >= 0 {
		// The first "]" closes an innermost group: the last "[" before it is its opener.
		closing := strings.IndexByte(s, ']')
		opening := strings.LastIndexByte(s[:closing], '[')
		start := opening
		for start > 0 && isDigit(s[start-1]) {
			start--
		}
		count, _ := strconv.Atoi(s[start:opening])
		s = s[:start] + strings.Repeat(s[opening+1:closing], count) + s[closing+1:]
	}
	return s
}

func isDigit(character byte) bool {
	return '0' <= character && character <= '9'
}
