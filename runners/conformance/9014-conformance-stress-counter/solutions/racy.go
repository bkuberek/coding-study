package conformance_stress_counter

type StressCounter struct {
	count int
}

func NewStressCounter() *StressCounter {
	return &StressCounter{}
}

func (c *StressCounter) Increment() int {
	current := c.count
	c.count = current + 1
	return current + 1
}
