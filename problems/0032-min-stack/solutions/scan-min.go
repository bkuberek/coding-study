package min_stack

import "slices"

type MinStack struct {
	values []int
}

func NewMinStack() *MinStack {
	return &MinStack{}
}

func (s *MinStack) Push(value int) {
	s.values = append(s.values, value)
}

func (s *MinStack) Pop() {
	s.values = s.values[:len(s.values)-1]
}

func (s *MinStack) Top() int {
	return s.values[len(s.values)-1]
}

func (s *MinStack) GetMin() int {
	// slices.Min scans every value: O(n) per call.
	return slices.Min(s.values)
}
