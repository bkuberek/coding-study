package group_anagrams

import "slices"

func groupAnagrams(strs []string) [][]string {
	groups := make(map[string][]string)
	for _, word := range strs {
		letters := []byte(word)
		slices.Sort(letters)
		key := string(letters)
		groups[key] = append(groups[key], word)
	}
	result := make([][]string, 0, len(groups))
	for _, group := range groups {
		result = append(result, group)
	}
	return result
}
