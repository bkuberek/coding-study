package decode_ways

const notComputed = -1

func numDecodings(s string) int {
	memo := make([]int, len(s))
	for start := range memo {
		memo[start] = notComputed
	}

	// waysFrom returns the number of readings of the suffix s[start:].
	var waysFrom func(start int) int
	waysFrom = func(start int) int {
		if start == len(s) {
			return 1
		}
		if s[start] == '0' {
			return 0
		}
		if memo[start] == notComputed {
			count := waysFrom(start + 1)
			if start+1 < len(s) {
				if pair := int(s[start]-'0')*10 + int(s[start+1]-'0'); pair >= 10 && pair <= 26 {
					count += waysFrom(start + 2)
				}
			}
			memo[start] = count
		}
		return memo[start]
	}

	return waysFrom(0)
}
