package valid_palindrome

import "slices"

func isPalindrome(s string) bool {
	cleaned := make([]byte, 0, len(s))
	for i := 0; i < len(s); i++ {
		if character := s[i]; isAlphanumeric(character) {
			cleaned = append(cleaned, toLower(character))
		}
	}
	reversed := slices.Clone(cleaned)
	slices.Reverse(reversed)
	return slices.Equal(cleaned, reversed)
}

func isAlphanumeric(character byte) bool {
	return 'a' <= character && character <= 'z' ||
		'A' <= character && character <= 'Z' ||
		'0' <= character && character <= '9'
}

func toLower(character byte) byte {
	if 'A' <= character && character <= 'Z' {
		return character + ('a' - 'A')
	}
	return character
}
