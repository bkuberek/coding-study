package longest_palindromic_substring

func longestPalindrome(s string) string {
	n := len(s)
	// isPalindrome[i][j] tells whether s[i..j] (inclusive) is a palindrome.
	isPalindrome := make([][]bool, n)
	for i := range isPalindrome {
		isPalindrome[i] = make([]bool, n)
		isPalindrome[i][i] = true
	}
	bestStart, bestLength := 0, 1
	for length := 2; length <= n; length++ {
		for i := 0; i+length <= n; i++ {
			j := i + length - 1
			if s[i] == s[j] && (length == 2 || isPalindrome[i+1][j-1]) {
				isPalindrome[i][j] = true
				bestStart, bestLength = i, length
			}
		}
	}
	return s[bestStart : bestStart+bestLength]
}
