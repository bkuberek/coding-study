package three_sum

import "slices"

func threeSum(nums []int) [][]int {
	values := slices.Clone(nums)
	slices.Sort(values)
	var triples [][]int
	for i := 0; i < len(values)-2; i++ {
		if i > 0 && values[i] == values[i-1] {
			continue
		}
		seen := make(map[int]bool)
		lastLargest, appended := 0, false
		for j := i + 1; j < len(values); j++ {
			middle := -values[i] - values[j]
			if seen[middle] && !(appended && values[j] == lastLargest) {
				triples = append(triples, []int{values[i], middle, values[j]})
				lastLargest, appended = values[j], true
			}
			seen[values[j]] = true
		}
	}
	return triples
}
