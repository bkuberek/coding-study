package palindrome_partitioning

import "slices"

func partition(s string) [][]string {
	n := len(s)
	// palindrome[i][j]: whether s[i..j] reads the same both ways. Row i depends on row i + 1.
	palindrome := make([][]bool, n)
	for i := range palindrome {
		palindrome[i] = make([]bool, n)
	}
	for i := n - 1; i >= 0; i-- {
		for j := i; j < n; j++ {
			palindrome[i][j] = s[i] == s[j] && (j-i < 2 || palindrome[i+1][j-1])
		}
	}

	var result [][]string
	var pieces []string

	var cutFrom func(start int)
	cutFrom = func(start int) {
		if start == n {
			result = append(result, slices.Clone(pieces))
			return
		}
		for end := start; end < n; end++ {
			if palindrome[start][end] {
				pieces = append(pieces, s[start:end+1])
				cutFrom(end + 1)
				pieces = pieces[:len(pieces)-1]
			}
		}
	}

	cutFrom(0)
	return result
}
