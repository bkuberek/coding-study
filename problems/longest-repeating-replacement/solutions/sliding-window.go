package longest_repeating_replacement

const alphabetSize = 26

func characterReplacement(s string, k int) int {
	var counts [alphabetSize]int
	most, left, best := 0, 0, 0
	for right := 0; right < len(s); right++ {
		letter := s[right] - 'A'
		counts[letter]++
		most = max(most, counts[letter])
		if right-left+1-most > k {
			counts[s[left]-'A']--
			left++
		}
		best = max(best, right-left+1)
	}
	return best
}
