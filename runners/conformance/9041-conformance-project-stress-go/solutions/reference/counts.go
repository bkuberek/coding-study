package tally

import "sync"

// counts are the counts by key; every read and write holds the mutex.
type counts struct {
	mutex  sync.Mutex
	values map[string]int
}

func newCounts() *counts {
	return &counts{values: map[string]int{}}
}

func (c *counts) add(key string, amount int) int {
	c.mutex.Lock()
	defer c.mutex.Unlock()
	c.values[key] += amount
	return c.values[key]
}

func (c *counts) of(key string) int {
	c.mutex.Lock()
	defer c.mutex.Unlock()
	return c.values[key]
}

func (c *counts) take(key string, amount int) bool {
	c.mutex.Lock()
	defer c.mutex.Unlock()
	if c.values[key] < amount {
		return false
	}
	c.values[key] -= amount
	return true
}
