package sliding_window_maximum

import "container/heap"

// positionHeap is a max-heap of positions in nums, ordered by the value at each position.
// container/heap builds a min-heap from Less, so Less asks for the larger value.
type positionHeap struct {
	positions []int
	nums      []int
}

func (h *positionHeap) Len() int { return len(h.positions) }

func (h *positionHeap) Less(a, b int) bool {
	return h.nums[h.positions[a]] > h.nums[h.positions[b]]
}

func (h *positionHeap) Swap(a, b int) {
	h.positions[a], h.positions[b] = h.positions[b], h.positions[a]
}

func (h *positionHeap) Push(position any) {
	h.positions = append(h.positions, position.(int))
}

func (h *positionHeap) Pop() any {
	last := len(h.positions) - 1
	position := h.positions[last]
	h.positions = h.positions[:last]
	return position
}

func maxSlidingWindow(nums []int, k int) []int {
	pending := &positionHeap{nums: nums}
	maxima := make([]int, 0, len(nums)-k+1)
	for right := range nums {
		heap.Push(pending, right)
		if right >= k-1 {
			for pending.positions[0] <= right-k {
				heap.Pop(pending)
			}
			maxima = append(maxima, nums[pending.positions[0]])
		}
	}
	return maxima
}
