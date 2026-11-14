package range_module

const (
	empty = iota
	covered
	mixed
)

const (
	rangeLow  = 1
	rangeHigh = 1_000_000_000 // every range lies inside [1, 10^9)
)

// node is empty or covered with no children, or mixed with both children.
type node struct {
	state       int
	left, right *node
}

type RangeModule struct {
	root *node
}

func NewRangeModule() *RangeModule {
	return &RangeModule{root: &node{state: empty}}
}

func (m *RangeModule) AddRange(left int, right int) {
	assign(m.root, rangeLow, rangeHigh, left, right, covered)
}

func (m *RangeModule) QueryRange(left int, right int) bool {
	return isCovered(m.root, rangeLow, rangeHigh, left, right)
}

func (m *RangeModule) RemoveRange(left int, right int) {
	assign(m.root, rangeLow, rangeHigh, left, right, empty)
}

func assign(n *node, low, high, left, right, value int) {
	if right <= low || high <= left {
		return
	}
	if left <= low && high <= right {
		n.state, n.left, n.right = value, nil, nil
		return
	}
	if n.left == nil {
		// A uniform node is split: both halves inherit its state.
		n.left, n.right = &node{state: n.state}, &node{state: n.state}
	}
	middle := low + (high-low)/2
	assign(n.left, low, middle, left, right, value)
	assign(n.right, middle, high, left, right, value)
	if agreed := n.left.state; agreed == n.right.state && agreed != mixed {
		n.state, n.left, n.right = agreed, nil, nil // both halves agree: collapse
	} else {
		n.state = mixed
	}
}

func isCovered(n *node, low, high, left, right int) bool {
	if right <= low || high <= left {
		return true
	}
	if n.left == nil {
		return n.state == covered
	}
	middle := low + (high-low)/2
	return isCovered(n.left, low, middle, left, right) && isCovered(n.right, middle, high, left, right)
}
