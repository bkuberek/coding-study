package store

// counts is the stock by name.
type counts map[string]int

func (c counts) add(name string, count int) int {
	c[name] += count
	return c[name]
}
