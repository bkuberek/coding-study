package min_stack

type MinStack struct {
	values []int
	// The minimums in the order they took effect; the last one is the current minimum.
	minimums []int
}

func NewMinStack() *MinStack {
	return &MinStack{}
}

func (s *MinStack) Push(value int) {
	s.values = append(s.values, value)
	// <= keeps one copy per equal minimum, so popping one copy keeps the others.
	if len(s.minimums) == 0 || value <= s.GetMin() {
		s.minimums = append(s.minimums, value)
	}
}

func (s *MinStack) Pop() {
	last := len(s.values) - 1
	if s.values[last] == s.GetMin() {
		s.minimums = s.minimums[:len(s.minimums)-1]
	}
	s.values = s.values[:last]
}

func (s *MinStack) Top() int {
	return s.values[len(s.values)-1]
}

func (s *MinStack) GetMin() int {
	return s.minimums[len(s.minimums)-1]
}
