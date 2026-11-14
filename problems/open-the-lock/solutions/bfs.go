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

type state struct {
	setting string
	moves   int
}

func openLock(deadends []string, target string) int {
	// Dead ends behave like settings that were already visited: the search never enters them.
	seen := make(map[string]bool, len(deadends))
	for _, deadend := range deadends {
		seen[deadend] = true
	}
	if seen[start] {
		return -1
	}
	seen[start] = true
	queue := []state{{start, 0}}
	for len(queue) > 0 {
		current := queue[0]
		queue = queue[1:]
		if current.setting == target {
			return current.moves
		}
		for _, following := range turns(current.setting) {
			if !seen[following] {
				seen[following] = true
				queue = append(queue, state{following, current.moves + 1})
			}
		}
	}
	return -1
}
