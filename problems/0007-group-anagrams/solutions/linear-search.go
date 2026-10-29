package group_anagrams

import "slices"

func groupAnagrams(strs []string) [][]string {
	var keys []string
	var groups [][]string
	for _, word := range strs {
		key := sortedLetters(word)
		if index := slices.Index(keys, key); index >= 0 {
			groups[index] = append(groups[index], word)
		} else {
			keys = append(keys, key)
			groups = append(groups, []string{word})
		}
	}
	return groups
}

func sortedLetters(word string) string {
	letters := []byte(word)
	slices.Sort(letters)
	return string(letters)
}
