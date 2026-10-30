package generate_parentheses

import "bytes"

// isBalanced reports whether the brackets are correctly nested. The depth is the height a stack
// of unmatched "(" would have.
func isBalanced(brackets []byte) bool {
	depth := 0
	for _, bracket := range brackets {
		if bracket == '(' {
			depth++
		} else {
			depth--
		}
		if depth < 0 {
			return false
		}
	}
	return depth == 0
}

func generateParenthesis(n int) []string {
	var result []string
	size := 2 * n
	// opening holds the positions of the "(" characters in increasing order, starting with
	// 0..n-1; the loop steps through every choice of n positions out of 2n in lexicographic order.
	opening := make([]int, n)
	for i := range opening {
		opening[i] = i
	}
	for {
		brackets := bytes.Repeat([]byte{')'}, size)
		for _, position := range opening {
			brackets[position] = '('
		}
		if isBalanced(brackets) {
			result = append(result, string(brackets))
		}
		// Advance the rightmost position that can still move right, and reset those after it.
		i := n - 1
		for i >= 0 && opening[i] == size-n+i {
			i--
		}
		if i < 0 {
			return result
		}
		opening[i]++
		for j := i + 1; j < n; j++ {
			opening[j] = opening[j-1] + 1
		}
	}
}
