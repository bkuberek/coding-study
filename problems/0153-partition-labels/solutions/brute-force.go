package partition_labels

import "strings"

func partitionLabels(s string) []int {
	var sizes []int
	start := 0
	for start < len(s) {
		// The piece must reach the last copy of every letter it contains.
		end := strings.LastIndexByte(s, s[start])
		for position := start; position <= end; position++ {
			end = max(end, strings.LastIndexByte(s, s[position]))
		}
		sizes = append(sizes, end-start+1)
		start = end + 1
	}
	return sizes
}
