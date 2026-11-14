package phone_letter_combinations

// keypad lists the letters of the digits '2' to '9', in that order.
var keypad = [8]string{"abc", "def", "ghi", "jkl", "mno", "pqrs", "tuv", "wxyz"}

func letterCombinations(digits string) []string {
	if digits == "" {
		return nil
	}
	var words []string
	letters := make([]byte, len(digits))

	var fill func(slot int)
	fill = func(slot int) {
		if slot == len(digits) {
			words = append(words, string(letters))
			return
		}
		for _, letter := range []byte(keypad[digits[slot]-'2']) {
			letters[slot] = letter
			fill(slot + 1)
		}
	}

	fill(0)
	return words
}
