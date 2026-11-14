// Package tally declares the entry type: cstudy grades Tally, built with NewTally.
package tally

// Tally counts per key; goroutines share it from level 2.
type Tally struct {
	counts *counts
}

// NewTally returns a tally in which every key counts 0.
func NewTally() *Tally {
	return &Tally{counts: newCounts()}
}

// Add adds amount to the count of key and returns the new count.
func (t *Tally) Add(key string, amount int) int {
	return t.counts.add(key, amount)
}

// Count returns the count of key.
func (t *Tally) Count(key string) int {
	return t.counts.of(key)
}

// Take removes amount from the count of key, unless the count is lower.
func (t *Tally) Take(key string, amount int) bool {
	return t.counts.take(key, amount)
}
