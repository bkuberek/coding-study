package word_break

import "strings"

const (
	unknown int8 = iota
	splittable
	unsplittable
)

func wordBreak(s string, wordDict []string) bool {
	memo := make([]int8, len(s))

	// canSplitFrom reports whether the suffix s[start:] can be split into dictionary words.
	var canSplitFrom func(start int) bool
	canSplitFrom = func(start int) bool {
		if start == len(s) {
			return true
		}
		if memo[start] == unknown {
			verdict := unsplittable
			for _, word := range wordDict {
				if strings.HasPrefix(s[start:], word) && canSplitFrom(start+len(word)) {
					verdict = splittable
					break
				}
			}
			memo[start] = verdict
		}
		return memo[start] == splittable
	}

	return canSplitFrom(0)
}
