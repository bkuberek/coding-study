package top_k_frequent_elements

import "container/heap"

type entry struct {
	value, count int
}

// weakestFirst is a min-heap by count: its root is the weakest of the entries kept so far.
type weakestFirst []entry

func (h weakestFirst) Len() int           { return len(h) }
func (h weakestFirst) Less(i, j int) bool { return h[i].count < h[j].count }
func (h weakestFirst) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }
func (h *weakestFirst) Push(x any)        { *h = append(*h, x.(entry)) }
func (h *weakestFirst) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

func topKFrequent(nums []int, k int) []int {
	counts := make(map[int]int)
	for _, value := range nums {
		counts[value]++
	}
	kept := make(weakestFirst, 0, k)
	for value, count := range counts {
		if len(kept) < k {
			heap.Push(&kept, entry{value, count})
		} else if count > kept[0].count {
			kept[0] = entry{value, count}
			heap.Fix(&kept, 0)
		}
	}
	answer := make([]int, len(kept))
	for i, e := range kept {
		answer[i] = e.value
	}
	return answer
}
