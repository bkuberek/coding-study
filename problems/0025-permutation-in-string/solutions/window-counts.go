package permutation_in_string

const alphabetSize = 26

func checkInclusion(pattern string, text string) bool {
	width := len(pattern)
	if width > len(text) {
		return false
	}
	var need, window [alphabetSize]int
	for i := 0; i < width; i++ {
		need[pattern[i]-'a']++
	}
	for right := 0; right < len(text); right++ {
		window[text[right]-'a']++
		if right >= width {
			window[text[right-width]-'a']--
		}
		if right >= width-1 && window == need {
			return true
		}
	}
	return false
}
