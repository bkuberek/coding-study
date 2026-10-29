package conformance_stress_counter

import "sync"

type StressCounter struct {
	mu    sync.Mutex
	count int
}

func NewStressCounter() *StressCounter {
	return &StressCounter{}
}

func (c *StressCounter) Increment() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.count++
	return c.count
}
