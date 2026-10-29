package conformance_op_error

type Counter struct {
	count int
}

func NewCounter() *Counter {
	return &Counter{}
}

func (c *Counter) Increment() int {
	c.count++
	return c.count
}

func (c *Counter) Fail() int {
	panic("counter failure")
}
