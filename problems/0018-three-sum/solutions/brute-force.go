package three_sum

import "slices"

func threeSum(nums []int) [][]int {
	values := slices.Clone(nums)
	slices.Sort(values)
	n := len(values)
	var triples [][]int
	for i := 0; i < n-2; i++ {
		if i > 0 && values[i] == values[i-1] {
			continue
		}
		for j := i + 1; j < n-1; j++ {
			if j > i+1 && values[j] == values[j-1] {
				continue
			}
			third := -values[i] - values[j]
			// The membership test scans values[j+1:]: one check per element.
			if slices.Contains(values[j+1:], third) {
				triples = append(triples, []int{values[i], values[j], third})
			}
		}
	}
	return triples
}
