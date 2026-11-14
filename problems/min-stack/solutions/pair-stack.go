package min_stack

// entry holds a value and the minimum of this value and everything below it.
type entry struct {
	value, minimum int
}

type MinStack struct {
	entries []entry
}

func NewMinStack() *MinStack {
	return &MinStack{}
}

func (s *MinStack) Push(value int) {
	minimum := value
	if len(s.entries) > 0 {
		minimum = min(value, s.GetMin())
	}
	s.entries = append(s.entries, entry{value, minimum})
}

func (s *MinStack) Pop() {
	s.entries = s.entries[:len(s.entries)-1]
}

func (s *MinStack) Top() int {
	return s.entries[len(s.entries)-1].value
}

func (s *MinStack) GetMin() int {
	return s.entries[len(s.entries)-1].minimum
}
