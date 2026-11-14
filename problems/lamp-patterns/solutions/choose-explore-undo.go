package lamp_patterns

func lampPatterns(n int) []string {
	var result []string
	lamps := make([]byte, 0, n)

	var extend func()
	extend = func() {
		if len(lamps) == n {
			result = append(result, string(lamps))
			return
		}
		lamps = append(lamps, '0')   // choose: off
		extend()                     // explore
		lamps = lamps[:len(lamps)-1] // undo
		// Prune: a lamp may be on only when its left neighbour is off (or missing).
		if len(lamps) == 0 || lamps[len(lamps)-1] == '0' {
			lamps = append(lamps, '1')
			extend()
			lamps = lamps[:len(lamps)-1]
		}
	}

	extend()
	return result
}
