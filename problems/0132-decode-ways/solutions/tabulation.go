package decode_ways

func numDecodings(s string) int {
	// ways[i] is the number of readings of the prefix s[:i]; the empty prefix has one.
	ways := make([]int, len(s)+1)
	ways[0] = 1
	for i := 1; i <= len(s); i++ {
		if s[i-1] != '0' {
			ways[i] += ways[i-1]
		}
		if i >= 2 {
			if pair := int(s[i-2]-'0')*10 + int(s[i-1]-'0'); pair >= 10 && pair <= 26 {
				ways[i] += ways[i-2]
			}
		}
	}
	return ways[len(s)]
}
