package generate_parentheses

func generateParenthesis(n int) []string {
	var result []string
	brackets := make([]byte, 0, 2*n)

	var extend func(opened, closed int)
	extend = func(opened, closed int) {
		if closed == n {
			result = append(result, string(brackets))
			return
		}
		if opened < n {
			brackets = append(brackets, '(')
			extend(opened+1, closed)
			brackets = brackets[:len(brackets)-1]
		}
		// A ")" is allowed only while it has an unmatched "(" to close.
		if closed < opened {
			brackets = append(brackets, ')')
			extend(opened, closed+1)
			brackets = brackets[:len(brackets)-1]
		}
	}

	extend(0, 0)
	return result
}
