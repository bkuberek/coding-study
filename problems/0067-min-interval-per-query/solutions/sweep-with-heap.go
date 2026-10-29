package min_interval_per_query

import (
	"cmp"
	"container/heap"
	"slices"
)

// candidate is an interval that starts at or before the current query.
type candidate struct{ size, right int }

// candidateHeap is a min-heap ordered by (size, right), for container/heap.
type candidateHeap []candidate

func (h candidateHeap) Len() int { return len(h) }
func (h candidateHeap) Less(i, j int) bool {
	if h[i].size != h[j].size {
		return h[i].size < h[j].size
	}
	return h[i].right < h[j].right
}
func (h candidateHeap) Swap(i, j int) { h[i], h[j] = h[j], h[i] }
func (h *candidateHeap) Push(x any)   { *h = append(*h, x.(candidate)) }
func (h *candidateHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

func minInterval(intervals [][]int, queries []int) []int {
	byLeft := slices.Clone(intervals)
	slices.SortFunc(byLeft, slices.Compare[[]int])
	answer := make([]int, len(queries))
	for i := range answer {
		answer[i] = -1
	}
	order := make([]int, len(queries))
	for i := range order {
		order[i] = i
	}
	slices.SortStableFunc(order, func(a, b int) int { return cmp.Compare(queries[a], queries[b]) })
	candidates := &candidateHeap{}
	added := 0
	for _, index := range order {
		query := queries[index]
		for added < len(byLeft) && byLeft[added][0] <= query {
			left, right := byLeft[added][0], byLeft[added][1]
			heap.Push(candidates, candidate{size: right - left + 1, right: right})
			added++
		}
		// An interval that ends before this query also ends before every later one.
		for candidates.Len() > 0 && (*candidates)[0].right < query {
			heap.Pop(candidates)
		}
		if candidates.Len() > 0 {
			answer[index] = (*candidates)[0].size
		}
	}
	return answer
}
