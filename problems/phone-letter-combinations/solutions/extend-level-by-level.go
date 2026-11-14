package phone_letter_combinations

// keypad lists the letters of the digits '2' to '9', in that order.
var keypad = [8]string{"abc", "def", "ghi", "jkl", "mno", "pqrs", "tuv", "wxyz"}

func letterCombinations(digits string) []string {
	if digits == "" {
		return nil
	}
	words := []string{""}
	for _, digit := range digits {
		letters := keypad[digit-'2']
		next := make([]string, 0, len(words)*len(letters))
		for _, word := range words {
			for _, letter := range letters {
				next = append(next, word+string(letter))
			}
		}
		words = next
	}
	return words
}
