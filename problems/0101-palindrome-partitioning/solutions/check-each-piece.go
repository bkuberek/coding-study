package palindrome_partitioning

import "slices"

func partition(s string) [][]string {
	var result [][]string
	var pieces []string

	isPalindrome := func(left, right int) bool {
		for left < right {
			if s[left] != s[right] {
				return false
			}
			left++
			right--
		}
		return true
	}

	var cutFrom func(start int)
	cutFrom = func(start int) {
		if start == len(s) {
			result = append(result, slices.Clone(pieces))
			return
		}
		for end := start; end < len(s); end++ {
			if isPalindrome(start, end) {
				pieces = append(pieces, s[start:end+1])
				cutFrom(end + 1)
				pieces = pieces[:len(pieces)-1]
			}
		}
	}

	cutFrom(0)
	return result
}
