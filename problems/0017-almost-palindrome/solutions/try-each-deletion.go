package almost_palindrome

func validPalindrome(s string) bool {
	if isPalindrome(s) {
		return true
	}
	for index := 0; index < len(s); index++ {
		if isPalindrome(s[:index] + s[index+1:]) {
			return true
		}
	}
	return false
}

func isPalindrome(s string) bool {
	for left, right := 0, len(s)-1; left < right; left, right = left+1, right-1 {
		if s[left] != s[right] {
			return false
		}
	}
	return true
}
