package tally

import (
	"runtime"
	"sync"
)

// counts are the counts by key; add reads a count under the mutex, lets it go, then writes it
// under the mutex again, so another add in between is lost.
type counts struct {
	mutex  sync.Mutex
	values map[string]int
}

func newCounts() *counts {
	return &counts{values: map[string]int{}}
}

func (c *counts) add(key string, amount int) int {
	count := c.of(key) + amount
	runtime.Gosched()
	c.mutex.Lock()
	defer c.mutex.Unlock()
	c.values[key] = count
	return count
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
