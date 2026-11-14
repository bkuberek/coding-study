package min_remove_to_balance

import "slices"

func minRemoveToMakeValid(s string) string {
	// Pass 1, left to right: drop every closer that finds nothing open.
	kept := make([]byte, 0, len(s))
	openCount := 0
	for i := 0; i < len(s); i++ {
		character := s[i]
		if character == ')' {
			if openCount == 0 {
				continue
			}
			openCount--
		} else if character == '(' {
			openCount++
		}
		kept = append(kept, character)
	}
	// Pass 2, right to left: drop the last openCount openers, which are never closed.
	result := make([]byte, 0, len(kept))
	for i := len(kept) - 1; i >= 0; i-- {
		character := kept[i]
		if character == '(' && openCount > 0 {
			openCount--
			continue
		}
		result = append(result, character)
	}
	slices.Reverse(result)
	return string(result)
}
