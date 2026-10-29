package three_sum

import "slices"

func threeSum(nums []int) [][]int {
	values := slices.Clone(nums)
	slices.Sort(values)
	n := len(values)
	var triples [][]int
	for i := 0; i < n-2; i++ {
		if values[i] > 0 {
			break
		}
		if i > 0 && values[i] == values[i-1] {
			continue
		}
		left, right := i+1, n-1
		for left < right {
			total := values[i] + values[left] + values[right]
			switch {
			case total < 0:
				left++
			case total > 0:
				right--
			default:
				triples = append(triples, []int{values[i], values[left], values[right]})
				left++
				right--
				for left < right && values[left] == values[left-1] {
					left++
				}
			}
		}
	}
	return triples
}
