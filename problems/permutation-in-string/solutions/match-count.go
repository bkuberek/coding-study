package permutation_in_string

const alphabetSize = 26

func checkInclusion(pattern string, text string) bool {
	width := len(pattern)
	if width > len(text) {
		return false
	}
	// surplus[letter] is the window's count of letter minus the pattern's.
	var surplus [alphabetSize]int
	for i := 0; i < width; i++ {
		surplus[pattern[i]-'a']--
	}
	balanced := 0
	for _, value := range surplus {
		if value == 0 {
			balanced++
		}
	}
	shift := func(letter byte, delta int) {
		if surplus[letter] == 0 {
			balanced--
		}
		surplus[letter] += delta
		if surplus[letter] == 0 {
			balanced++
		}
	}
	for right := 0; right < len(text); right++ {
		shift(text[right]-'a', 1)
		if right >= width {
			shift(text[right-width]-'a', -1)
		}
		if balanced == alphabetSize {
			return true
		}
	}
	return false
}
