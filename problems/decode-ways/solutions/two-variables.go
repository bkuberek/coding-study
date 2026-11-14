package decode_ways

func numDecodings(s string) int {
	// Before digit i: oneBack counts readings of s[:i] and twoBack those of s[:i-1].
	twoBack, oneBack := 0, 1
	for i := 0; i < len(s); i++ {
		current := 0
		if s[i] != '0' {
			current = oneBack
		}
		if i > 0 {
			if pair := int(s[i-1]-'0')*10 + int(s[i]-'0'); pair >= 10 && pair <= 26 {
				current += twoBack
			}
		}
		twoBack, oneBack = oneBack, current
	}
	return oneBack
}
