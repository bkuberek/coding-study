package word_break

func wordBreak(s string, wordDict []string) bool {
	words := make(map[string]bool, len(wordDict))
	longest := 0
	for _, word := range wordDict {
		words[word] = true
		longest = max(longest, len(word))
	}
	// ok[i] is true when the prefix s[:i] can be split into dictionary words.
	ok := make([]bool, len(s)+1)
	ok[0] = true
	for end := 1; end <= len(s); end++ {
		for start := max(0, end-longest); start < end; start++ {
			if ok[start] && words[s[start:end]] {
				ok[end] = true
				break
			}
		}
	}
	return ok[len(s)]
}
