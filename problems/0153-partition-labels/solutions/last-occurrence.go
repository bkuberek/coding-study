package partition_labels

func partitionLabels(s string) []int {
	var last [26]int
	for index := 0; index < len(s); index++ {
		last[s[index]-'a'] = index
	}
	var sizes []int
	start, end := 0, 0
	for index := 0; index < len(s); index++ {
		end = max(end, last[s[index]-'a'])
		if index == end {
			// Every letter seen since `start` has no copy after this point: cut here.
			sizes = append(sizes, end-start+1)
			start = index + 1
		}
	}
	return sizes
}
