package median_data_stream

import "slices"

type MedianFinder struct {
	values []int // every number so far, ascending
}

func NewMedianFinder() *MedianFinder {
	return &MedianFinder{}
}

func (f *MedianFinder) AddNum(num int) {
	// The binary search is O(log n); shifting the tail to open the slot is O(n).
	position, _ := slices.BinarySearch(f.values, num)
	f.values = slices.Insert(f.values, position, num)
}

func (f *MedianFinder) FindMedian() float64 {
	middle := len(f.values) / 2
	if len(f.values)%2 == 1 {
		return float64(f.values[middle])
	}
	return float64(f.values[middle-1]+f.values[middle]) / 2
}
