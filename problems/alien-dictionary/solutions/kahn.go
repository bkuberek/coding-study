package alien_dictionary

const letters = 26

func alienOrder(words []string) string {
	var present [letters]bool
	for _, word := range words {
		for i := 0; i < len(word); i++ {
			present[word[i]-'a'] = true
		}
	}
	// before[x][y]: letter x must come before letter y. A matrix dedupes repeated rules.
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
	var waiting [letters]int
	for x := 0; x < letters; x++ {
		for y := 0; y < letters; y++ {
			if before[x][y] {
				waiting[y]++
			}
		}
	}
	var ready []int
	letterCount := 0
	for x := 0; x < letters; x++ {
		if present[x] {
			letterCount++
			if waiting[x] == 0 {
				ready = append(ready, x)
			}
		}
	}
	order := make([]byte, 0, letterCount)
	for len(ready) > 0 {
		x := ready[0]
		ready = ready[1:]
		order = append(order, byte('a'+x))
		for y := 0; y < letters; y++ {
			if before[x][y] {
				waiting[y]--
				if waiting[y] == 0 {
					ready = append(ready, y)
				}
			}
		}
	}
	if len(order) == letterCount {
		return string(order)
	}
	return ""
}
