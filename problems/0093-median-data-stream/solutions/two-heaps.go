package median_data_stream

import "container/heap"

// intHeap implements heap.Interface as a min-heap of ints. The lower half stores negated values,
// which turns the same type into a max-heap.
type intHeap []int

func (h intHeap) Len() int           { return len(h) }
func (h intHeap) Less(i, j int) bool { return h[i] < h[j] }
func (h intHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }

func (h *intHeap) Push(value any) {
	*h = append(*h, value.(int))
}

func (h *intHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

type MedianFinder struct {
	// low is the smaller half as a max-heap (values negated); high is the larger half as a
	// min-heap. low holds as many values as high, or one more.
	low, high intHeap
}

func NewMedianFinder() *MedianFinder {
	return &MedianFinder{}
}

func (f *MedianFinder) AddNum(num int) {
	// Route the number through low so that every value in low stays <= every value in high.
	heap.Push(&f.low, -num)
	heap.Push(&f.high, -heap.Pop(&f.low).(int))
	if f.high.Len() > f.low.Len() {
		heap.Push(&f.low, -heap.Pop(&f.high).(int))
	}
}

func (f *MedianFinder) FindMedian() float64 {
	if f.low.Len() > f.high.Len() {
		return float64(-f.low[0])
	}
	return float64(-f.low[0]+f.high[0]) / 2
}
