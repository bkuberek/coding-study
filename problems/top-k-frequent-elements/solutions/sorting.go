package top_k_frequent_elements

import (
	"cmp"
	"slices"
)

func topKFrequent(nums []int, k int) []int {
	counts := make(map[int]int)
	for _, value := range nums {
		counts[value]++
	}
	byCount := make([]int, 0, len(counts))
	for value := range counts {
		byCount = append(byCount, value)
	}
	slices.SortFunc(byCount, func(a, b int) int {
		return cmp.Compare(counts[b], counts[a])
	})
	return byCount[:k]
}
