package valid_palindrome

func isPalindrome(s string) bool {
	left, right := 0, len(s)-1
	for left < right {
		switch {
		case !isAlphanumeric(s[left]):
			left++
		case !isAlphanumeric(s[right]):
			right--
		case toLower(s[left]) != toLower(s[right]):
			return false
		default:
			left++
			right--
		}
	}
	return true
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
