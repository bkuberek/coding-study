package valid_anagram

const alphabetSize = 26

func isAnagram(s string, t string) bool {
	if len(s) != len(t) {
		return false
	}
	var counts [alphabetSize]int
	for i := 0; i < len(s); i++ {
		counts[s[i]-'a']++
	}
	for i := 0; i < len(t); i++ {
		index := t[i] - 'a'
		counts[index]--
		if counts[index] < 0 {
			return false
		}
	}
	return true
}
