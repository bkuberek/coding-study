// Package tally declares the entry type: cstudy grades Tally, built with NewTally.
package tally

// Tally counts per key.
type Tally struct{}

// NewTally returns a tally in which every key counts 0.
func NewTally() *Tally {
	return &Tally{}
}

// Add adds amount to the count of key and returns the new count.
func (t *Tally) Add(key string, amount int) int {
	panic("not implemented")
}

// Count returns the count of key.
func (t *Tally) Count(key string) int {
	panic("not implemented")
}
