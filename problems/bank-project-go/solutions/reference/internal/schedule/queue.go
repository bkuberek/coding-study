package schedule

import "cmp"

// queue is a min-heap of bookings, earliest due first and equal due times in booking order.
// It implements heap.Interface; container/heap's functions keep it a heap.
type queue []*booking

func (q queue) Len() int { return len(q) }

// Less breaks ties on the due time by booking number. container/heap is not stable: with
// due times alone, equal entries come out in whatever order the heap's swaps left them.
func (q queue) Less(i, j int) bool {
	return cmp.Or(cmp.Compare(q[i].Due, q[j].Due), cmp.Compare(q[i].number, q[j].number)) < 0
}

func (q queue) Swap(i, j int) { q[i], q[j] = q[j], q[i] }

// Push appends x; heap.Push calls it, then moves the new entry up to its place.
func (q *queue) Push(x any) {
	*q = append(*q, x.(*booking))
}

// Pop removes the last entry; heap.Pop calls it after swapping the front entry there.
func (q *queue) Pop() any {
	old := *q
	last := old[len(old)-1]
	old[len(old)-1] = nil
	*q = old[:len(old)-1]
	return last
}
