package valid_parentheses

import "strings"

var pairs = []string{"()", "[]", "{}"}

func isValid(s string) bool {
	for {
		shorter := s
		for _, pair := range pairs {
			shorter = strings.ReplaceAll(shorter, pair, "")
		}
		if len(shorter) == len(s) {
			// Nothing left to delete: balanced exactly when nothing is left at all.
			return s == ""
		}
		s = shorter
	}
}
