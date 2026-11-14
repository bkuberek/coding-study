package last_stone_weight

import (
	"container/heap"
	"slices"
)

// maxHeap implements heap.Interface with the heaviest stone at index 0.
type maxHeap []int

func (h maxHeap) Len() int           { return len(h) }
func (h maxHeap) Less(i, j int) bool { return h[i] > h[j] }
func (h maxHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }

func (h *maxHeap) Push(weight any) {
	*h = append(*h, weight.(int))
}

func (h *maxHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

func lastStoneWeight(stones []int) int {
	pile := maxHeap(slices.Clone(stones))
	heap.Init(&pile)
	for pile.Len() > 1 {
		heaviest := heap.Pop(&pile).(int)
		second := heap.Pop(&pile).(int)
		if heaviest != second {
			heap.Push(&pile, heaviest-second)
		}
	}
	if pile.Len() == 0 {
		return 0
	}
	return pile[0]
}
