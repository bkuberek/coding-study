package two_sum_sorted

import "slices"

func twoSumSorted(numbers []int, target int) []int {
	for i, value := range numbers {
		complement := target - value
		offset, found := slices.BinarySearch(numbers[i+1:], complement)
		if found {
			return []int{i, i + 1 + offset}
		}
	}
	return nil
}
