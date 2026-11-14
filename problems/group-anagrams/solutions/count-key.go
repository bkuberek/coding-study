package group_anagrams

const alphabetSize = 26

func groupAnagrams(strs []string) [][]string {
	groups := make(map[[alphabetSize]int][]string)
	for _, word := range strs {
		// Arrays are comparable in Go, so the 26 counts are the map key themselves.
		var counts [alphabetSize]int
		for i := 0; i < len(word); i++ {
			counts[word[i]-'a']++
		}
		groups[counts] = append(groups[counts], word)
	}
	result := make([][]string, 0, len(groups))
	for _, group := range groups {
		result = append(result, group)
	}
	return result
}
