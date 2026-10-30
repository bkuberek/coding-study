package maximize_capital

import (
	"cmp"
	"container/heap"
	"slices"
)

// maxHeap implements heap.Interface with the largest profit at index 0.
type maxHeap []int

func (h maxHeap) Len() int           { return len(h) }
func (h maxHeap) Less(i, j int) bool { return h[i] > h[j] }
func (h maxHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }

func (h *maxHeap) Push(profit any) {
	*h = append(*h, profit.(int))
}

func (h *maxHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

type project struct {
	capital, profit int
}

func findMaximizedCapital(k int, w int, profits []int, capital []int) int {
	projects := make([]project, len(profits))
	for i := range profits {
		projects[i] = project{capital[i], profits[i]}
	}
	// Cheapest requirement first.
	slices.SortFunc(projects, func(a, b project) int { return cmp.Compare(a.capital, b.capital) })
	affordable := &maxHeap{}
	unlocked := 0
	for range k {
		// Capital only grows, so every project unlocked once stays affordable.
		for unlocked < len(projects) && projects[unlocked].capital <= w {
			heap.Push(affordable, projects[unlocked].profit)
			unlocked++
		}
		if affordable.Len() == 0 {
			break // nothing affordable now, and capital cannot grow any more
		}
		w += heap.Pop(affordable).(int)
	}
	return w
}
