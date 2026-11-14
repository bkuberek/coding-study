package longest_repeating_replacement

const alphabetSize = 26

func characterReplacement(s string, k int) int {
	best := 0
	for start := 0; start < len(s); start++ {
		var counts [alphabetSize]int
		most := 0
		for end := start; end < len(s); end++ {
			letter := s[end] - 'A'
			counts[letter]++
			most = max(most, counts[letter])
			if end-start+1-most > k {
				break
			}
			best = max(best, end-start+1)
		}
	}
	return best
}
