package open_the_lock

const start = "0000"

// turns returns the eight settings one move away: each wheel up or down by one, wrapping around.
func turns(setting string) []string {
	result := make([]string, 0, 8)
	for wheel := 0; wheel < 4; wheel++ {
		digit := int(setting[wheel] - '0')
		for _, turn := range [2]int{1, 9} {
			following := []byte(setting)
			following[wheel] = byte('0' + (digit+turn)%10)
			result = append(result, string(following))
		}
	}
	return result
}

func openLock(deadends []string, target string) int {
	blocked := make(map[string]bool, len(deadends))
	for _, deadend := range deadends {
		blocked[deadend] = true
	}
	if blocked[start] {
		return -1
	}
	if target == start {
		return 0
	}
	// Two frontiers grow toward each other; moves counts the levels expanded so far.
	near, far := map[string]bool{start: true}, map[string]bool{target: true}
	seen := map[string]bool{start: true, target: true}
	moves := 0
	for len(near) > 0 && len(far) > 0 {
		if len(near) > len(far) {
			near, far = far, near // always expand the smaller frontier
		}
		moves++
		followingLevel := make(map[string]bool)
		for setting := range near {
			for _, following := range turns(setting) {
				if far[following] {
					return moves
				}
				if !seen[following] && !blocked[following] {
					seen[following] = true
					followingLevel[following] = true
				}
			}
		}
		near = followingLevel
	}
	return -1
}
