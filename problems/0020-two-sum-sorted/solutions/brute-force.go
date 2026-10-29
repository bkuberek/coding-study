package two_sum_sorted

import "slices"

func twoSumSorted(numbers []int, target int) []int {
	for i, value := range numbers {
		if offset := slices.Index(numbers[i+1:], target-value); offset >= 0 {
			return []int{i, i + 1 + offset}
		}
	}
	return nil
}
