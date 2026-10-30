package alien_dictionary

const (
	letters   = 26
	unvisited = 0
	onPath    = 1
	done      = 2
)

func alienOrder(words []string) string {
	var present [letters]bool
	for _, word := range words {
		for i := 0; i < len(word); i++ {
			present[word[i]-'a'] = true
		}
	}
	// before[x][y]: letter x must come before letter y.
	var before [letters][letters]bool
	for i := 0; i+1 < len(words); i++ {
		first, second := words[i], words[i+1]
		shorter := min(len(first), len(second))
		k := 0
		for k < shorter && first[k] == second[k] {
			k++
		}
		if k < shorter {
			before[first[k]-'a'][second[k]-'a'] = true
		} else if len(first) > len(second) {
			return "" // a word placed before its own proper prefix
		}
	}
	var state [letters]int
	// Each letter lands in finished after every letter that must follow it.
	finished := make([]byte, 0, letters)

	// visit emits everything after x, then x; false if a rule loops back.
	var visit func(x int) bool
	visit = func(x int) bool {
		state[x] = onPath
		for y := 0; y < letters; y++ {
			if !before[x][y] {
				continue
			}
			if state[y] == onPath || (state[y] == unvisited && !visit(y)) {
				return false
			}
		}
		state[x] = done
		finished = append(finished, byte('a'+x))
		return true
	}

	for x := 0; x < letters; x++ {
		if present[x] && state[x] == unvisited && !visit(x) {
			return ""
		}
	}
	for i, j := 0, len(finished)-1; i < j; i, j = i+1, j-1 {
		finished[i], finished[j] = finished[j], finished[i]
	}
	return string(finished)
}
