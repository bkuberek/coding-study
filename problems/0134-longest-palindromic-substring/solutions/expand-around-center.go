package longest_palindromic_substring

func longestPalindrome(s string) string {
	bestStart, bestLength := 0, 1
	// Center c sits on character c/2 when c is even, between two characters when c is odd.
	for center := 0; center < 2*len(s)-1; center++ {
		left, right := center/2, (center+1)/2
		for left >= 0 && right < len(s) && s[left] == s[right] {
			left--
			right++
		}
		// The loop overshoots by one on each side: the palindrome is s[left+1 .. right-1].
		if right-left-1 > bestLength {
			bestStart, bestLength = left+1, right-left-1
		}
	}
	return s[bestStart : bestStart+bestLength]
}
