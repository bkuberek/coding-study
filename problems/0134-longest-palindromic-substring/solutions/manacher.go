package longest_palindromic_substring

func longestPalindrome(s string) string {
	// Interleave a separator so every palindrome has odd length: "ab" becomes "|a|b|".
	t := make([]byte, 2*len(s)+1)
	for i := range t {
		t[i] = '|'
	}
	for i := 0; i < len(s); i++ {
		t[2*i+1] = s[i]
	}
	// radius[i] is how far the palindrome centered at t[i] extends to each side.
	radius := make([]int, len(t))
	center, right := 0, 0 // the palindrome reaching furthest right is t[2*center-right .. right]
	for i := range t {
		if i < right {
			// Mirror of i around center; its radius is valid up to the right boundary.
			radius[i] = min(right-i, radius[2*center-i])
		}
		for i-radius[i]-1 >= 0 && i+radius[i]+1 < len(t) && t[i-radius[i]-1] == t[i+radius[i]+1] {
			radius[i]++
		}
		if i+radius[i] > right {
			center, right = i, i+radius[i]
		}
	}
	best := 0
	for i, r := range radius {
		if r > radius[best] {
			best = i
		}
	}
	// A radius r around position i of t covers r characters of s starting at (i - r) / 2.
	start := (best - radius[best]) / 2
	return s[start : start+radius[best]]
}
